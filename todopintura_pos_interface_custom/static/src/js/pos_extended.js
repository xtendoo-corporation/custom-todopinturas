// Código simplificado para Todo Pintura POS - Solo ocultar panel de productos
console.log('=== TODO PINTURA POS: Cargando módulo ===');

// Función para esperar a que el DOM esté listo
function waitForDOM(callback) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback);
    } else {
        callback();
    }
}

// Función principal que se ejecuta cuando el DOM está listo
function initTodoPinturaPOS() {
    console.log('Todo Pintura POS: Iniciando...');

    // Ocultar panel de productos
    function hideProductPanel() {
        const rightPane = document.querySelector('.pos .product-screen .rightpane');
        if (rightPane) {
            rightPane.style.display = 'none';
            console.log('Panel de productos ocultado');
        }

        const leftPane = document.querySelector('.pos .product-screen .leftpane');
        if (leftPane) {
            leftPane.style.width = '100%';
            console.log('Panel izquierdo expandido');
        }
    }

    // Limpiar cualquier contenedor personalizado existente
    function removeCustomContainers() {
        const customContainers = document.querySelectorAll('#todo-pintura-totals, #todo-pintura-integrated, #unified-order-container');
        customContainers.forEach(container => {
            if (container) {
                container.remove();
                console.log('Contenedor personalizado eliminado');
            }
        });
    }

    // Función principal de inicialización
    function initialize() {
        console.log('Inicializando Todo Pintura POS...');

        // Verificar que estamos en el POS
        const posScreen = document.querySelector('.pos .product-screen');
        if (!posScreen) {
            console.log('No estamos en la pantalla del POS');
            return false;
        }

        // Limpiar contenedores personalizados
        removeCustomContainers();

        // Ocultar panel de productos
        hideProductPanel();

        console.log('Todo Pintura POS inicializado correctamente');
        return true;
    }

    // Función para reintentar inicialización
    function retryInitialization() {
        let attempts = 0;
        const maxAttempts = 3;

        function attempt() {
            attempts++;
            console.log(`Intento de inicialización ${attempts}/${maxAttempts}`);

            if (initialize()) {
                console.log('Inicialización exitosa');
                return;
            }

            if (attempts < maxAttempts) {
                setTimeout(attempt, 2000);
            } else {
                console.log('Se agotaron los intentos de inicialización');
            }
        }

        attempt();
    }

    // Ejecutar inicialización
    retryInitialization();

    // Limpiar contenedores personalizados periódicamente
    setInterval(() => {
        removeCustomContainers();
    }, 5000);

    console.log('=== TODO PINTURA POS: Módulo cargado completamente ===');
}

// Esperar a que el DOM esté listo antes de ejecutar
waitForDOM(initTodoPinturaPOS);

// También ejecutar en load por si acaso
if (typeof window !== 'undefined') {
    window.addEventListener('load', initTodoPinturaPOS);
}

// También agregar el objeto global por compatibilidad
if (typeof window !== 'undefined') {
    window.todoPinturaExtended = {
        init: function() {
            console.log('Método init llamado');
            initTodoPinturaPOS();
        }
    };
}
