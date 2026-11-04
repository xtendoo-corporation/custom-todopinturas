# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Adoption of records created by hand (RPC) before this module existed.

The module data is declared with external ids. Records that already exist in
the database without one would be duplicated on install/update, so they are
matched by name and given the external id declared in the data files. The
module data then updates them in place.
"""

import csv
import logging
import re
import unicodedata
from collections import defaultdict

from lxml import etree

from odoo import Command
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

MODULE = "todopintura_user_groups"
LEGACY_FIELD = "x_warehouse_ids"
NEW_FIELD = "allowed_warehouse_ids"
WAREHOUSE_REF = re.compile(r"ref\('(\w+)'\)")
GROUP_REF = re.compile(r"ref\('([\w.]+)'\)")


def pre_init_hook(env):
    adopt_manual_records(env)


def post_init_hook(env):
    migrate_legacy_warehouse_field(env)


def _normalize(text):
    text = (text or "").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def _parse(path):
    with file_open(f"{MODULE}/{path}", "rb") as handle:
        return etree.parse(handle).getroot()


def _is_noupdate(root):
    return root.get("noupdate") in ("1", "true")


def _declared_names(root, model):
    """Map xml id -> name for the ``<record>`` nodes of the given model."""
    names = {}
    for record in root.iter("record"):
        name_node = record.find("field[@name='name']")
        if record.get("model") == model and name_node is not None:
            names[record.get("id")] = (name_node.text or "").strip()
    return names


def _declared_menu_paths(root):
    """Map xml id -> 'Root/Child' (``complete_name``) for the ``<menuitem>`` nodes."""
    items = {item.get("id"): item for item in root.iter("menuitem")}

    def path(item):
        parent = items.get(item.get("parent"))
        prefix = f"{path(parent)}/" if parent is not None else ""
        return prefix + item.get("name")

    return {xml_id: path(item) for xml_id, item in items.items()}


def _unmanaged(env, model):
    """Records of ``model`` without any external id (hand-made records)."""
    Model = env[model].with_context(active_test=False)
    managed_ids = set(
        env["ir.model.data"].search([("model", "=", model)]).mapped("res_id")
    )
    return Model.search([("id", "not in", list(managed_ids))])


def _assign(env, model, expected, key, noupdate=False):
    """Give the declared external id to the unmanaged record with the same key."""
    taken = set(
        env["ir.model.data"]
        .search([("module", "=", MODULE), ("model", "=", model)])
        .mapped("name")
    )
    by_key = defaultdict(list)
    for record in _unmanaged(env, model):
        by_key[_normalize(key(record))].append(record)
    values = []
    for xml_id, expected_key in expected.items():
        if xml_id in taken:
            continue
        matches = by_key.get(_normalize(expected_key), [])
        if len(matches) == 1:
            values.append(
                {
                    "xml_id": f"{MODULE}.{xml_id}",
                    "record": matches[0],
                    "noupdate": noupdate,
                }
            )
        elif matches:
            _logger.warning(
                "%s %r: %d candidates, not adopted (%s)",
                model,
                expected_key,
                len(matches),
                xml_id,
            )
        else:
            _logger.info("%s %r: nothing to adopt (%s)", model, expected_key, xml_id)
    env["ir.model.data"]._update_xmlids(values)
    return len(values)


def _adopt_security(env):
    categories = _parse("data/res_groups_category.xml")
    security = _parse("security/security.xml")
    _assign(
        env,
        "ir.module.category",
        _declared_names(categories, "ir.module.category"),
        lambda rec: rec.name,
    )
    for model in ("res.groups.privilege", "res.groups"):
        _assign(env, model, _declared_names(security, model), lambda rec: rec.name)


def _adopt_menus(env):
    _assign(
        env,
        "ir.ui.menu",
        _declared_menu_paths(_parse("views/menus.xml")),
        lambda rec: rec.complete_name,
    )


def _adopt_rules(env):
    """Global rules built on the manual field are adopted by model."""
    root = _parse("security/ir_rule.xml")
    expected = {}
    for record in root.iter("record"):
        domain = record.find("field[@name='domain_force']")
        if record.get("model") != "ir.rule" or NEW_FIELD not in (domain.text or ""):
            continue
        model_ref = record.find("field[@name='model_id']").get("ref")
        expected[record.get("id")] = env.ref(model_ref).model
    legacy = _unmanaged(env, "ir.rule").filtered(
        lambda rule: LEGACY_FIELD in (rule.domain_force or "") and not rule.groups
    )
    by_model = defaultdict(list)
    for rule in legacy:
        by_model[rule.model_id.model].append(rule)
    values = []
    for xml_id, model in expected.items():
        if len(by_model.get(model, [])) == 1:
            values.append(
                {"xml_id": f"{MODULE}.{xml_id}", "record": by_model[model][0]}
            )
    env["ir.model.data"]._update_xmlids(values)


def _adopt_access(env):
    """Access rows are matched by (model, group) whatever their name is."""
    with file_open(f"{MODULE}/security/ir.model.access.csv", "r") as handle:
        rows = list(csv.DictReader(handle))
    unmanaged = _unmanaged(env, "ir.model.access")
    by_pair = {(acl.model_id.id, acl.group_id.id): acl for acl in unmanaged}
    values = []
    for row in rows:
        group = env.ref(f"{MODULE}.{row['group_id:id']}", raise_if_not_found=False)
        model = env.ref(row["model_id:id"], raise_if_not_found=False)
        acl = group and model and by_pair.get((model.id, group.id))
        if acl:
            values.append({"xml_id": f"{MODULE}.{row['id']}", "record": acl})
    env["ir.model.data"]._update_xmlids(values)


def _adopt_pos_and_warehouses(env):
    data = _parse("data/pos_config.xml")
    noupdate = _is_noupdate(data)
    configs = _declared_names(data, "pos.config")
    _assign(env, "pos.config", configs, lambda rec: rec.name, noupdate)
    # A warehouse is found through the POS that works on it, then by name.
    warehouse_of_config = {}
    for record in data.iter("record"):
        if record.get("model") == "pos.config":
            search = record.find("field[@name='picking_type_id']").get("search")
            warehouse_of_config[record.get("id")] = WAREHOUSE_REF.search(search).group(
                1
            )
    managed = env["ir.model.data"].search(
        [("module", "=", MODULE), ("model", "=", "pos.config")]
    )
    values = []
    taken = set(
        env["ir.model.data"]
        .search([("module", "=", MODULE), ("model", "=", "stock.warehouse")])
        .mapped("name")
    )
    for link in managed:
        warehouse_xml_id = warehouse_of_config.get(link.name)
        config = env["pos.config"].browse(link.res_id)
        warehouse = config.picking_type_id.warehouse_id
        if warehouse_xml_id and warehouse_xml_id not in taken and warehouse:
            taken.add(warehouse_xml_id)
            values.append(
                {
                    "xml_id": f"{MODULE}.{warehouse_xml_id}",
                    "record": warehouse,
                    "noupdate": noupdate,
                }
            )
    env["ir.model.data"]._update_xmlids(values)
    _assign(
        env,
        "stock.warehouse",
        _declared_names(data, "stock.warehouse"),
        lambda rec: rec.name,
        noupdate,
    )


def _adopt_pricelist(env):
    root = _parse("data/pricelist_outlet.xml")
    _assign(
        env,
        "product.pricelist",
        _declared_names(root, "product.pricelist"),
        lambda rec: rec.name,
        _is_noupdate(root),
    )


def _remove_legacy_views(env):
    """The form view that placed the manual field is replaced by the module's."""
    views = (
        env["ir.ui.view"]
        .with_context(active_test=False)
        .search([("model", "=", "res.users"), ("inherit_id", "!=", False)])
    )
    legacy = views.filtered(
        lambda view: (
            LEGACY_FIELD in (view.arch_db or "")
            and not view.get_external_id().get(view.id, "").startswith(f"{MODULE}.")
        )
    )
    legacy.unlink()


def _clear_standard_menu_links(env):
    """Previous versions linked these groups to standard Odoo menus.

    Those menus are replaced by the module's own menus, so the links are removed
    to keep restricted users away from the standard menu tree.
    """
    group_ids = (
        env["ir.model.data"]
        .search([("module", "=", MODULE), ("model", "=", "res.groups")])
        .mapped("res_id")
    )
    menus = (
        env["ir.ui.menu"]
        .with_context(active_test=False)
        .search([("group_ids", "in", group_ids)])
    )
    for menu in menus:
        if not menu.get_external_id().get(menu.id, "").startswith(f"{MODULE}."):
            menu.group_ids = [Command.unlink(group_id) for group_id in group_ids]


def adopt_manual_records(env):
    """Run before the module data is loaded (install and update)."""
    _adopt_security(env)
    _clear_standard_menu_links(env)
    _adopt_menus(env)
    _adopt_rules(env)
    _adopt_access(env)
    _adopt_pos_and_warehouses(env)
    _adopt_pricelist(env)
    _remove_legacy_views(env)


def migrate_legacy_warehouse_field(env):
    """Copy x_warehouse_ids into allowed_warehouse_ids and drop the manual field."""
    legacy = env["ir.model.fields"].search(
        [("model", "=", "res.users"), ("name", "=", LEGACY_FIELD)]
    )
    if not legacy:
        return
    users = env["res.users"].with_context(active_test=False).search([])
    users = users.filtered(lambda user: user[LEGACY_FIELD])
    for user in users:
        user.allowed_warehouse_ids = user[LEGACY_FIELD]
    _logger.info("Copied %s into %s for %d users", LEGACY_FIELD, NEW_FIELD, len(users))
    legacy.unlink()


def reset_declared_implied_groups(env):
    """Make the implied groups of the module groups match security.xml.

    ``Command.link`` only adds on update, so an implication removed from the
    data file would otherwise survive.
    """
    root = _parse("security/security.xml")
    declared = defaultdict(list)  # a group can be extended by several records
    for record in root.iter("record"):
        node = record.find("field[@name='implied_ids']")
        if record.get("model") != "res.groups" or node is None:
            continue
        if "." in record.get("id"):  # standard group extended by the module
            continue
        declared[record.get("id")] += GROUP_REF.findall(node.get("eval") or "")
    for xml_id, refs in declared.items():
        group = env.ref(f"{MODULE}.{xml_id}", raise_if_not_found=False)
        if not group:
            continue
        implied = env["res.groups"].browse(
            env.ref(ref if "." in ref else f"{MODULE}.{ref}").id for ref in refs
        )
        group.implied_ids = [Command.set(implied.ids)]


def reset_declared_menu_actions(env):
    """Containers declared without action must not keep an adopted old one."""
    root = _parse("views/menus.xml")
    for item in root.iter("menuitem"):
        if item.get("action"):
            continue
        menu = env.ref(f"{MODULE}.{item.get('id')}", raise_if_not_found=False)
        if menu and menu.action:
            menu.action = False


def normalize_declared_records(env):
    """Make updated data exact: implications and actions removed from the data
    files are removed from the database too."""
    reset_declared_implied_groups(env)
    reset_declared_menu_actions(env)
