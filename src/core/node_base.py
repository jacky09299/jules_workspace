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

    def get_input_value(self, index: int):
        """Helper to get data from connected output of the previous node"""
        if index < 0 or index >= len(self.inputs):
            print(f"DEBUG [{self.title}] get_input: Index {index} out of range")
            return None
        port = self.inputs[index]
        if not port.connected_ports:
            print(f"DEBUG [{self.title}] get_input: Port {port.name} (idx {index}) not connected")
            return None
        
        other_port = port.connected_ports[0]
        val = other_port.value
        # Summarize value for logging
        try:
            val_str = str(val)
        except:
            val_str = "<Unprintable>"
            
        val_str = val_str[:50] + "..." if len(val_str) > 50 else val_str
        print(f"DEBUG [{self.title}] Input {index} ({port.name}) <- {val_str} (from {other_port.node.title})")
        return val

    def set_output_value(self, index: int, value: Any):
        if index >= 0 and index < len(self.outputs):
            self.outputs[index].value = value
            # Safe string conversion for arrays
            try:
                val_str = str(value)
            except:
                val_str = "<Unprintable>"
            
            val_str = val_str[:50] + "..." if len(val_str) > 50 else val_str
            print(f"DEBUG [{self.title}] Output {index} ({self.outputs[index].name}) set to {val_str}")

    def execute(self):
        """
        Main logic method. Subclasses must override this.
        Read inputs using get_input_value(), process, set outputs using set_output_value().
        """
        raise NotImplementedError("Node subclasses must implement execute()")

    def to_dict(self):
        """Serialization"""
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "parameters": self.parameters,
            "inputs": [p.id for p in self.inputs], # Just saving IDs might be enough, or save structure
            "outputs": [p.id for p in self.outputs]
        }
