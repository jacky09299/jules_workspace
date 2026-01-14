import uuid
from typing import List, Dict, Any, Optional
from src.core.datatypes import DataType

class Port:
    def __init__(self, node, name: str, data_type: DataType, is_output: bool = False):
        self.node = node
        self.name = name
        self.data_type = data_type
        self.is_output = is_output
        self.id = str(uuid.uuid4())
        self.value = None # Holds the data passed through this port
        self.connected_ports = [] # List of Port objects

    def connect(self, other_port):
        if self.is_output == other_port.is_output:
            raise ValueError("Cannot connect same type ports")
        self.connected_ports.append(other_port)
        other_port.connected_ports.append(self)

    def disconnect(self, other_port):
        if other_port in self.connected_ports:
            self.connected_ports.remove(other_port)
            if self in other_port.connected_ports:
                other_port.connected_ports.remove(self)

class Node:
    def __init__(self, title: str):
        self.id = str(uuid.uuid4())
        self.title = title
        self.inputs: List[Port] = []
        self.outputs: List[Port] = []
        self.parameters: Dict[str, Any] = {} # User configurable parameters
        self.x = 0
        self.y = 0

        # Mappings for dynamic parameter inputs
        # Map parameter_name -> input_port_index
        self.param_inputs: Dict[str, int] = {}

        # State
        self.is_dirty = True
        self.execution_error = None

    def add_input(self, name: str, data_type: DataType):
        port = Port(self, name, data_type, is_output=False)
        self.inputs.append(port)
        return port

    def add_output(self, name: str, data_type: DataType):
        port = Port(self, name, data_type, is_output=True)
        self.outputs.append(port)
        return port

    def remove_input(self, port: Port):
        """Removes an input port and disconnects it."""
        if port in self.inputs:
            # Disconnect all connections
            for other_port in list(port.connected_ports):
                port.disconnect(other_port)
            self.inputs.remove(port)

    def get_input_value(self, index: int):
        """Helper to get data from connected output of the previous node"""
        if index < 0 or index >= len(self.inputs):
            print(f"DEBUG [{self.title}] get_input: Index {index} out of range")
            return None
        port = self.inputs[index]
        if not port.connected_ports:
            # print(f"DEBUG [{self.title}] get_input: Port {port.name} (idx {index}) not connected")
            return None
        
        other_port = port.connected_ports[0]
        val = other_port.value
        # Summarize value for logging
        try:
            val_str = str(val)
        except:
            val_str = "<Unprintable>"
            
        val_str = val_str[:50] + "..." if len(val_str) > 50 else val_str
        # print(f"DEBUG [{self.title}] Input {index} ({port.name}) <- {val_str} (from {other_port.node.title})")
        return val

    def get_parameter(self, name: str):
        """
        Retrieves a parameter value.
        Prioritizes an input port if one is exposed and connected.
        Otherwise falls back to the internal parameters dict.
        """
        # Check if this parameter is exposed as an input
        if name in self.param_inputs:
            idx = self.param_inputs[name]
            val = self.get_input_value(idx)
            # If the port is connected and has a valid value (not None), use it.
            # However, sometimes None is a valid value passed from upstream.
            # But here, if the port is unconnected, get_input_value returns None.
            # We should check if connected.
            if idx < len(self.inputs):
                port = self.inputs[idx]
                if port.connected_ports:
                     return val

        # Fallback
        return self.parameters.get(name)

    def expose_parameter(self, name: str, data_type: DataType = DataType.ANY):
        """
        Converts a parameter into an input port.
        """
        if name not in self.parameters:
            print(f"Warning: Cannot expose unknown parameter '{name}'")
            return

        if name in self.param_inputs:
            print(f"Parameter '{name}' is already exposed.")
            return

        # Add input
        port = self.add_input(name, data_type)
        # Store index
        self.param_inputs[name] = len(self.inputs) - 1
        print(f"Exposed parameter '{name}' as input port index {self.param_inputs[name]}")

    def hide_parameter(self, name: str):
        """
        Removes the input port for a parameter, reverting to static value.
        """
        if name not in self.param_inputs:
            return

        idx = self.param_inputs[name]
        # We need to remove this port from self.inputs
        # But removing from list shifts indices of subsequent ports!
        # This breaks self.param_inputs mapping for other ports.

        # Strategy:
        # 1. Get the port object
        port_to_remove = self.inputs[idx]

        # 2. Remove it
        self.remove_input(port_to_remove)

        # 3. Clean up map
        del self.param_inputs[name]

        # 4. Re-index remaining param inputs
        # Since we removed one, any index > idx needs to be decremented.
        # But wait, we have mixed standard inputs and param inputs.
        # We need to rebuild the map or shift.
        # Actually, self.param_inputs stores the index.
        # Since inputs are ordered list, we just need to find where the others are now.
        # But we can't easily know which input corresponds to which param just by index.
        # We should probably store (name -> port_object) instead of index to be safe?
        # But get_input_value uses index.

        # Let's just iterate and rebuild map.
        # We need to know which port belongs to which param.
        # Maybe we can tag the port?

        # New approach: Param inputs are just inputs with name == param_name (usually).
        # We can just iterate self.inputs and check names?
        # Or just shift:
        keys_to_update = []
        for p_name, p_idx in self.param_inputs.items():
            if p_idx > idx:
                keys_to_update.append(p_name)

        for p_name in keys_to_update:
            self.param_inputs[p_name] -= 1

        print(f"Hidden parameter '{name}' input.")

    def set_output_value(self, index: int, value: Any):
        if index >= 0 and index < len(self.outputs):
            self.outputs[index].value = value
            # Safe string conversion for arrays
            try:
                val_str = str(value)
            except:
                val_str = "<Unprintable>"
            
            val_str = val_str[:50] + "..." if len(val_str) > 50 else val_str
            # print(f"DEBUG [{self.title}] Output {index} ({self.outputs[index].name}) set to {val_str}")

    def execute(self):
        """
        Main logic method. Subclasses must override this.
        Read inputs using get_input_value(), process, set outputs using set_output_value().
        """
        raise NotImplementedError("Node subclasses must implement execute()")

    def to_dict(self):
        """Serialization"""
        # We need to save which parameters are exposed
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "parameters": self.parameters,
            "param_inputs": self.param_inputs, # Save this state
            "inputs": [p.id for p in self.inputs],
            "outputs": [p.id for p in self.outputs]
        }
