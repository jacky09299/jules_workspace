import logging
import json

class SharedState:
    def __init__(self, config_file='shared_variables_config.json'): # Changed default filename
        self.variables = {}
        self.observers = {}
        self.config_file = config_file
        self._setup_logging()
        self.load_config() # Load config at initialization

    def _setup_logging(self):
        self.logger = logging.getLogger("ModularGUI")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.log("SharedState initialized")

    def get(self, key, default=None):
        return self.variables.get(key, default)

    def set(self, key, value):
        self.variables[key] = value
        self.log(f"Set variable '{key}' to '{value}'")
        self.notify_observers(key, value)

    def log(self, message, level=logging.INFO):
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.CRITICAL:
            self.logger.critical(message)

    def add_observer(self, key, callback):
        if key not in self.observers:
            self.observers[key] = []
        self.observers[key].append(callback)
        self.log(f"Added observer for variable '{key}'")

    def remove_observer(self, key, callback):
        if key in self.observers and callback in self.observers[key]:
            self.observers[key].remove(callback)
            if not self.observers[key]:
                del self.observers[key]
            self.log(f"Removed observer for variable '{key}'")

    def notify_observers(self, key, value):
        if key in self.observers:
            for callback in self.observers[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    self.log(f"Error notifying observer for '{key}': {e}", level=logging.ERROR)

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Assuming config directly stores variables for SharedState
                # Or specific keys like 'shared_variables'
                self.variables.update(config.get('shared_variables', {}))
                self.log(f"Configuration loaded from {self.config_file}")
        except FileNotFoundError:
            self.log(f"Configuration file {self.config_file} not found. Starting with default state.", level=logging.WARNING)
        except json.JSONDecodeError:
            self.log(f"Error decoding JSON from {self.config_file}. Starting with default state.", level=logging.ERROR)
        except Exception as e:
            self.log(f"An unexpected error occurred while loading config: {e}", level=logging.ERROR)


    def save_config(self):
        # This method might be more relevant for layout, but good to have a general idea
        # For now, let's assume we are saving the shared variables
        try:
            with open(self.config_file, 'w') as f:
                # Only saving self.variables for now, layout config will be separate
                json.dump({'shared_variables': self.variables}, f, indent=4)
            self.log(f"Shared state variables saved to {self.config_file}")
        except Exception as e:
            self.log(f"Error saving shared state to {self.config_file}: {e}", level=logging.ERROR)

if __name__ == '__main__':
    # Example Usage
    TEST_CONFIG_FILE = 'test_shared_variables_config.json' # Use a distinct test file name
    shared_state = SharedState(config_file=TEST_CONFIG_FILE)
    
    # Set some variables
    shared_state.set("username", "Alice")
    shared_state.set("theme", "dark")

    # Get variables
    print(f"Username: {shared_state.get('username')}")
    print(f"Theme: {shared_state.get('theme')}")
    print(f"NonExistent: {shared_state.get('non_existent_key', 'default_value')}")

    # Logging
    shared_state.log("This is an info message.")
    shared_state.log("This is a warning message.", level=logging.WARNING)

    # Observer pattern
    def theme_observer(key, value):
        print(f"OBSERVER: Theme changed! New theme: {value}")

    shared_state.add_observer("theme", theme_observer)
    shared_state.set("theme", "light") # This should trigger the observer

    # Save and load config (basic example for shared variables)
    shared_state.save_config()
    
    # Create a new instance to test loading
    new_shared_state = SharedState(config_file=TEST_CONFIG_FILE)
    print(f"Loaded Username: {new_shared_state.get('username')}")
    print(f"Loaded Theme: {new_shared_state.get('theme')}")
    
    # Clean up test file
    import os
    if os.path.exists(TEST_CONFIG_FILE):
        os.remove(TEST_CONFIG_FILE)
        print(f"Test config file '{TEST_CONFIG_FILE}' removed.")
    else:
        print(f"Test config file '{TEST_CONFIG_FILE}' not found, skipping removal.")
