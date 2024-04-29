"""Base class definitions for various types of fields that are used in a
	given binary protocol

This file can be imported as a module and contains the following classes:

	* Field - a base class representing some value as well as metadata and
		functions on how to pack/unpack it to/from a binary format.
	* IntField - A Field whose value is an int.
	* FloatField - An IntField whose value can be parsed as a floating point
		value.
	* BitField - An IntField whose only values can be 0 or 1.
	* BitEnabledField - A BitField where True represents the field being
		enabled and False represents it being disabled.
	* BitDisabledField - A BitField where False represents the field being
		enabled and True represents it being enabled.
	* EnumField - An IntField where the potential values represent some sort of
		non-numerical value.
	* ReservedField - An IntField with a variable length intended to act as a
		catch-all for all fields left undefined in a binary protocol.
	* StringField - A Field whose value is a str.
	* RawDataField - A Field whose value is a raw bytearray.
	* TimeField - A Field representing the number of seconds passed since
		midnight.
	* DateField - A TimeField with added functionality to represent a date.
	* BlockField - A Field whose value is some sort of complex object (typically
		a ProtocolBlock object).
	* BlockListField - A Field whose value is a list of some sort of complex
		object (typically a ProtocolBlock object).

	├─ Field 
	|  ├─ IntField
	|  |  ├─ FloatField
	|  |  ├─ BitField
	|  |  | ├─ BitEnabledField
	|  |  | ├─ BitDisabledField
	|  |  ├─ EnumField
	|  |  ├─ ReservedField
	|  ├─ StringField
	|  ├─ RawDataField
	|  ├─ TimeField
	|  |   ├─DateTimeField
	|  ├─ BlockField
	|  |   ├─BlockListField

Author:      Zach High-Leggett

Created:     December 2023
Updated:     December 18, 2023
"""

from abc import abstractmethod
from collections.abc import Iterator
from enum import Enum
from enum import IntFlag
from datetime import datetime
from datetime import timedelta
from BinaryTranslator.protocol_block import ProtocolBlock
from BinaryTranslator import bintools
import math
import warnings
import time
from BinaryTranslator import omnizdebug as dbg

class Field(ProtocolBlock):
	"""A base class representing a field in a binary protocol block.
	
	Attributes
	----------
	value : object
		The value held by the field in a particular binary message.
	bit_length : int
		The number number of bits intended to hold the field's value.
	BIT_LENGTH_MINIMUM : int
		The minimum possible value that can be held in bit_length bits.
	BIT_LENGTH_MAXIMUM : int
		The maximum possible value that can be held in bit_length bits.
	DESCRIPTION : str, default=""
		A description of what the field represents, intended to be overridden
			by subclasses.
	DEFAULT : None
		The default value to assign to fields of this type.
	
	Methods
	-------
	validate(val) (abstractmethod, classmethod)
		Checks that val is an acceptable value to be stored in this Field.
			Is implicitly called any time anything is assigned to the Field's
			value attribute. Returns val if validation is successful.
	pack(val) (abstractmethod, classmethod)
		Converts a human-readable value into a value understood internally
			within the field. For example, takes a raw floating-point gas
			reading and converts it to a packed integer value.
	enrich() (abstractmethod)
		Takes the Field's value and converts it into a human-friendly
			representation.
	"""
	
	BIT_LENGTH = None
	DESCRIPTION = ""
	DEFAULT = None
	
	def __init__(self, value):
		self.value = value
	
	def __setattr__(self, name, val):
		"""Overrides __setattr__ to run validate() on any assigned value before
			assigning it to the Field's value attribute.
		"""
		if name == "value":
			super().__setattr__(name, self.validate(val))
		else:
			super().__setattr__(name, val)
		
	def __str__(self):
		"""Returns the string representation of the Field's value attribute."""
		return str(self.value)
	
	def __repr__(self):
		"""Returns a string representation of the Field's most salient attributes."""
		return f"{type(self).__name__}; {self.bit_length}-bit value={self.value}"
	
	@classmethod
	@property
	def BIT_LENGTH_MINIMUM(cls):
		"""The minimum possible value that can be held in bit_length bits."""
		return 0
	
	@classmethod
	@property
	def BIT_LENGTH_MAXIMUM(cls):
		"""The maximum possible value that can be held in bit_length bits."""
		return 2 ** cls.BIT_LENGTH
	
	@property
	def bit_length(self):
		"""The number of bits that the field occupies in its binary protocol."""
		return self.BIT_LENGTH
	
	@classmethod
	@abstractmethod
	def validate(cls, val):
		"""A valitation function for a value to potentially be assigned as the
			Field's value attribute.
			
		Parameters
		----------
		val : object
		
		Raises
		------
		ValueError
			If the object fails validation.
			
		Returns
		-------
		object
			Returns val if validation is successful.
			
		"""
		pass
	
	@classmethod
	@abstractmethod
	def pack(cls, value):
		"""Converts a human-readable value into a value understood internally
			within the field.
		"""
		pass
	
	@abstractmethod
	def enrich(self):
		"""Takes the Field's value and converts it into a human-friendly
			representation.
		"""
		pass

class IntField(Field):
	"""A class representing an integer value stored in a field in a binary
		protocol block.
	
	Attributes
	----------
	value : int
	DEFAULT = 0
	BIT_LENGTH = 8
		The number of bits used by this field in its binary protocol.
			Intended to be overridden by subclasses.
	SIGNED : bool, default=False
		If True, Field can store signed integers (positive or negative).
		If False, Field can only store non-negative integers.
	MINIMUM : int, default=BIT_LENGTH_MINIMUM
		The smallest legal value when packing has been applied to it.
	MAXIMUM : int, default=BIT_LENGTH_MAXIMUM
		The largest legal value when packing has been applied to it.
	"""
	BIT_LENGTH = 8
	DEFAULT = 0
	SIGNED = False
	
	@classmethod
	@property
	def MINIMUM(cls):
		"""The smallest legal value when packing has been applied to it."""
		return cls.BIT_LENGTH_MINIMUM
	
	@classmethod
	@property
	def MAXIMUM(cls):
		"""The largest legal value when packing has been applied to it."""
		return cls.BIT_LENGTH_MAXIMUM
	
	# the maximum value that can be held in the available bits, should not be overridden
	@classmethod
	@property
	def BIT_LENGTH_MINIMUM(cls):
		"""The minimum possible value that can be held in bit_length bits."""
		if cls.SIGNED:
			return -(2 ** (cls.BIT_LENGTH - 1))
		else:
			return 0
	
	# the maximum value that can be held in the available bits, should not be overridden
	@classmethod
	@property
	def BIT_LENGTH_MAXIMUM(cls):
		"""The maximum possible value that can be held in bit_length bits."""
		if cls.SIGNED:
			return 2 ** (cls.BIT_LENGTH - 1) - 1
		else:
			return 2 ** cls.BIT_LENGTH - 1
	
	@classmethod
	def validate(cls, val, bit_min = None, bit_max = None, min = None, max = None):
		"""A validation function for an int to potentially be assigned as the
			IntField's value attribute.
			
		Parameters
		----------
		val : int
		min : int, optional
			Override the default minimum legal value.
		max : int, optional
			Override the default maximum legal value.
		
		Raises
		------
		OverflowError
			If the value is too small or too large to be contained within the
				allotted number of bits.
			
		Warns
		-----
		UserWarning
			If the value is outside of the specified minimum or maximum, but
				can still be stored in the allotted number of bits.
			
		Returns
		-------
		int
			Returns val if validation is successful.
		"""
		bit_min = bit_min or cls.BIT_LENGTH_MINIMUM
		bit_max = bit_max or cls.BIT_LENGTH_MAXIMUM
		min = min or cls.MINIMUM
		max = max or cls.MAXIMUM
		
		if val > bit_max:
			error_string = f"{cls.__name__} value {val} is too big to be contained within {cls.BIT_LENGTH} bits. Must be maximum of {bit_max}."
			dbg.error(error_string)
			raise OverflowError(error_string)
		if val < bit_min:
			error_string = f"{cls.__name__} value {val} is too small to be contained within {cls.BIT_LENGTH} bits. Must be minimum of {bit_min}."
			dbg.error(error_string)
			raise OverflowError(error_string)
		if val < min:
			warning_string = f"{cls.__name__} value {val} below defined minimum {min} but within protocol-supported range of [{bit_min}, {bit_max}]."
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
		if val > max:
			warning_string = f"{cls.__name__} value {val} above defined maximum {max} but within protocol-supported range of [{bit_min}, {bit_max}]."
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
			return val
		return val
	
	@classmethod
	def pack(cls, val):
		"""Converts a number value into a value that can be stored within
			the IntField.
			
		Parameters:
		-----------
		value : number
		
		Raises
		-------
		ValueError
			If value is too small or too large to be contained within the
				allotted bits, or
			If value is not divisible by the IntField's unpacked resolution.
			
		Returns
		-------
		int
		"""
		if val != int(val):
			error_string = f"{cls.__name__} value {val} must be in increments of {cls.UNPACKED_RESOLUTION}."
			raise ValueError(error_string)
		if val > cls.BIT_LENGTH_MAXIMUM:
			error_string = f"{cls.__name__} packed value {val} is too big to be contained within {cls.BIT_LENGTH} bits. Must be maximum of {cls.BIT_LENGTH_MAXIMUM}."
			raise ValueError(error_string)
		if val < cls.BIT_LENGTH_MINIMUM:
			error_string = f"{cls.__name__} packed value {val} is too small to be contained within {cls.BIT_LENGTH} bits. Must be minimum of {cls.BIT_LENGTH_MINIMUM}."
			raise ValueError(error_string)
		
		return int(val)
	
	def enrich(self):
		"""Unpacks the internally stored value into a meaningful value between
			the unpacked minimum and maximum value with the unpacked resolution.
		"""
		bound = lambda x: max(min(x, self.BIT_LENGTH_MAXIMUM), self.BIT_LENGTH_MINIMUM)
		return bound(self.value)
	
	@classmethod
	def from_bytes(cls, stream, num_bytes = 1, signed = False, consume = True, endianness = "little"):
		if num_bytes % 8 == 0:
			return bintools.get_int(stream, num_bytes, signed, consume, endianness)
		else:
			raise ValueError(f"Cannot get an even number of bytes for {num_bytes}-bitlength integer.")
	

	def to_bytes(self):
		return bintools.pack_int(self.value,  num_bytes = math.ceil(self.bit_length / 8), signed = self.SIGNED, endianness = "little")

class PackedIntField(IntField):
	"""A class representing an integer value stored in a field in a binary
		protocol block that can be unpacked to a more meaningful value.
	
	Attributes
	----------
	value : int
	DEFAULT = 0
	BIT_LENGTH = 8
		The number of bits used by this field in its binary protocol.
			Intended to be overridden by subclasses.
	SIGNED : bool, default=False
		If True, Field can store signed integers (positive or negative).
		If False, Field can only store non-negative integers.
	UNPACKED_MINIMUM : int
		The smallest legal value when packing has not been applied to it.
			Intended to be overridden by subclasses.
	UNPACKED_MAXIMUM : int
		The largest legal value when packing has not been applied to it.
			Intended to be overridden by subclasses.
	UNPACKED_RESOLUTION : int, default=1
		The absolute difference between two adjacent legal unpacked values.
			Intended to be overridden by subclasses.
	MINIMUM : int, default=BIT_LENGTH_MINIMUM
		The smallest legal value when packing has been applied to it.
	MAXIMUM : int, default=BIT_LENGTH_MAXIMUM
		The largest legal value when packing has been applied to it.
	RESOLUTION : int, default=1
		The absolute difference between two adjacent packed values.
	"""
	BIT_LENGTH = 8
	DEFAULT = 0
	SIGNED = False
		
	@classmethod
	@property
	def UNPACKED_MINIMUM(cls):
		"""The smallest legal value when packing has not been applied to it."""
		return cls.BIT_LENGTH_MINIMUM
	
	@classmethod
	@property
	def UNPACKED_MAXIMUM(cls):
		"""The largest legal value when packing has not been applied to it."""
		return cls.UNPACKED_MINIMUM + (cls.BIT_LENGTH_MAXIMUM * cls.UNPACKED_RESOLUTION)
	
	@classmethod
	@property
	def MINIMUM(cls):
		"""The smallest legal value when packing has been applied to it."""
		return cls.pack(cls.UNPACKED_MINIMUM)
	
	@classmethod
	@property
	def MAXIMUM(cls):
		"""The largest legal value when packing has been applied to it."""
		return cls.pack(cls.UNPACKED_MAXIMUM)
	
	# the maximum value that can be held in the available bits, should not be overridden
	@classmethod
	@property
	def BIT_LENGTH_MINIMUM(cls):
		"""The minimum possible value that can be held in bit_length bits."""
		if cls.SIGNED:
			return -(2 ** (cls.BIT_LENGTH - 1))
		else:
			return 0
	
	# the maximum value that can be held in the available bits, should not be overridden
	@classmethod
	@property
	def BIT_LENGTH_MAXIMUM(cls):
		"""The maximum possible value that can be held in bit_length bits."""
		if cls.SIGNED:
			return 2 ** (cls.BIT_LENGTH - 1) - 1
		else:
			return 2 ** cls.BIT_LENGTH - 1
		
	RESOLUTION          = 1
	UNPACKED_RESOLUTION = 1
	
	@classmethod
	def validate(cls, val, min = None, max = None, res = None):
		"""A validation function for an int to potentially be assigned as the
			IntField's value attribute.
			
		Parameters
		----------
		val : int
		min : int, optional
			Override the default minimum legal value.
		max : int, optional
			Override the default maximum legal value.
		res : int, optional
			Override the default resolution.
		
		Raises
		------
		OverflowError
			If the value is too small or too large to be contained within the
				allotted number of bits, or
			If the value is not divisible by the resolution.
			
		Warns
		-----
		UserWarning
			If the value is outside of the specified minimum or maximum, but
				can still be stored in the allotted number of bits.
			
		Returns
		-------
		int
			Returns val if validation is successful.
		"""
		bit_min = cls.BIT_LENGTH_MINIMUM
		bit_max = cls.BIT_LENGTH_MAXIMUM
		min = min or cls.MINIMUM
		max = max or cls.MAXIMUM
		res = res or cls.RESOLUTION
		
		if val > bit_max:
			error_string = f"{cls.__name__} value {val} is too big to be contained within {cls.BIT_LENGTH} bits. Must be maximum of {bit_max}."
			dbg.error(error_string)
			raise OverflowError(error_string)
		if val < bit_min:
			error_string = f"{cls.__name__} value {val} is too small to be contained within {cls.BIT_LENGTH} bits. Must be minimum of {bit_min}."
			dbg.error(error_string)
			raise OverflowError(error_string)
		if val < min:
			warning_string = f"{cls.__name__} value {val} below defined minimum {min} but within protocol-supported range of [{bit_min}, {bit_max}]."
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
		if val > max:
			warning_string = f"{cls.__name__} value {val} above defined maximum {max} but within protocol-supported range of [{bit_min}, {bit_max}]."
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
			return val
		if val / res != int(val / res):
			error_string = f"{cls.__name__} value {val} must be in increments of {res}."
			dbg.error(error_string)
			raise ValueError(error_string)
		return val
	
	@classmethod
	def pack(cls, val):
		"""Converts a number value into a value that can be stored within
			the IntField.
			
		Parameters:
		-----------
		value : number
		
		Raises
		-------
		ValueError
			If value is too small or too large to be contained within the
				allotted bits, or
			If value is not divisible by the IntField's unpacked resolution.
			
		Returns
		-------
		int
		"""
		packed = (val - cls.UNPACKED_MINIMUM) / cls.UNPACKED_RESOLUTION
		
		
		if packed != int(packed):
			error_string = f"{cls.__name__} value {val} must be in increments of {cls.UNPACKED_RESOLUTION}."
			raise ValueError(error_string)
		if packed > cls.BIT_LENGTH_MAXIMUM:
			error_string = f"{cls.__name__} packed value {packed} is too big to be contained within {cls.BIT_LENGTH} bits. Must be maximum of {cls.BIT_LENGTH_MAXIMUM}."
			raise ValueError(error_string)
		if packed < cls.BIT_LENGTH_MINIMUM:
			error_string = f"{cls.__name__} packed value {packed} is too small to be contained within {cls.BIT_LENGTH} bits. Must be minimum of {cls.BIT_LENGTH_MINIMUM}."
			raise ValueError(error_string)
		
		return int(packed)
	
	def enrich(self):
		"""Unpacks the internally stored value into a meaningful value between
			the unpacked minimum and maximum value with the unpacked resolution.
		"""
		bound = lambda x: max(min(x, self.UNPACKED_MAXIMUM), self.UNPACKED_MINIMUM)
		unpacked_value = self.UNPACKED_MINIMUM + (self.value * self.UNPACKED_RESOLUTION)
		return bound(unpacked_value)

class IEEEFloatField(IntField):
	"""A class representing a floating-point value packed into a field in a
		binary protocol.
		
	Uses python's float packing as opposed to a min/max/resolution approach.
	"""
	BIT_LENGTH = 32
	SIGNED = True
	
	@classmethod
	def validate(cls, value):
		if float(value) != value:
			warning_string = f"{cls.__name__} value {value} is not supported by IEEE floats and will be rounded."
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
		return float(value)
	
	@classmethod
	def pack(cls, value):
		return cls.validate(value)
	
	@classmethod
	def from_bytes(cls, stream, consume = True, endianness = "little"):
		return bintools.get_float(stream, consume = consume, endianness = endianness)
	
	def to_bytes(self):
		return bintools.pack_float(self.value)

class DynamicLengthIntField(IntField):
	
	@property
	def minimum(self):
		"""The smallest legal value when packing has been applied to it."""
		return self.bit_length_minimum
	
	@property
	def maximum(self):
		"""The largest legal value when packing has been applied to it."""
		return self.bit_length_maximum
	
	@property
	def bit_length_minimum(self):
		"""The minimum possible value that can be held in bit_length bits."""
		if self.SIGNED:
			return -(2 ** (self.bit_length - 1))
		else:
			return 0
		
	@property
	def bit_length_maximum(self):
		"""The maximum possible value that can be held in bit_length bits."""
		if self.SIGNED:
			return 2 ** (self.bit_length - 1) - 1
		else:
			return 2 ** self.bit_length - 1
	
	@property
	def bit_length(self):
		return self.size
	
	def __init__(self, value, size = 8):
		self.size = size
		super().__init__(value)
		
	def validate(self, value):
		return super().validate(value, bit_max = 2 ** self.size)
	
	def enrich(self):
		return self.value
	
	
class ReservedField(DynamicLengthIntField):
	"""A class representing an undefined or reserved field in a binary
		protocol. Bit length is now a property of ReservedField objects
		instead of the ReservedField class.
		
	Attributes
	----------
	bit_length : int, default=8
		The number of bits being reserved by this field.
	MAXIMUM = 0
	"""
	MAXIMUM = 0
		
class MetaEnum(type):
	"""Acts as a metaclass for EnumField which enables direct access to
		Enum values in the DefinedFields enumeration to be accessed directly
		as attributes of the EnumField object.
	"""
	
	def __getattr__(self, __name):
		"""Overrides __getattr__ so that if a requested attribute is not found
			among the field's properties, python will search within the
			EnumValues Enum first before giving up.
	
		Raises
		------
		AttributeError
			If a requested attribute cannot be found within the field nor its
				EnumValues.
		"""
		if __name in dir(self):
			return self.__dir__(__name)
		
		if __name in dir(self.EnumValues):
			return self.EnumValues[__name].value
		
		raise AttributeError(self.__name__ + " object " + type(self).__name__ + " has no attribute " + __name)

class BitField(IntField):
	"""An IntField with its length restricted to a single bit."""
	BIT_LENGTH = 1
	
	@classmethod
	def pack(cls, val):
		"""Packs a boolean value as a bit.
		
		Parameters
		----------
		val : bool
		
		Returns
		-------
		int
			0 if val is False
			1 if val is True
		"""
		if val:
			return 1
		else:
			return 0
		
	def enrich(self):
		"""Convert the internal int value to a boolean.
		
		Returns
		-------
		bool
			True if bit value is 1.
			False if bit value is 0.
		"""
		if self.value == 1:
			return True
		else:
			return False

class EnumField(IntField, metaclass=MetaEnum):
	"""A class representing an integer corresponding to a defined enumeration.
	
	Attributes
	----------
	value : int
	EnumValues : enum.Enum
		An enumeration of special values that the field recognizes.
	MINIMUM : int, default=BIT_LENGTH_MINIMUM
		The smallest value defined within EnumValues.
	MAXIMUM : int, default=BIT_LENGTH_MAXIMUM
		The largest value defined within EnumValues
		
	Methods	
	-------
	validate(val) (classmethod)
		Checks for val within EnumValues and returns it if it exists.
		Otherwise uses IntField's validation mechanism.
		Notably this means that if a value is not defined in EnumValues,
			but could fit inside the field's allotted bits, it will pass
			validation.
	enrich(val)
		Checks for val within EnumValues and returns the corresponding
			key string as a human-readable value.
	"""
	
	class EnumValues(Enum):
		"""An enumeration intended to be overridden by child classes that
			defines non-integer represented by the integer stored as the 
			EnumField's value attribute.
		"""
		pass
	
	@classmethod
	@property
	def MINIMUM(cls):
		"""The smallest value defined within EnumValues.
		
		If EnumValues is empty, will return the minimum allowable value
			that can fit within the field's allotted bits.
		"""
		if len(cls.EnumValues) == 0:
			return cls.BIT_LENGTH_MINIMUM
		return min([v.value for v in list(cls.EnumValues)])
	
	@classmethod
	@property
	def MAXIMUM(cls):
		"""The largest value defined within EnumValues.
		
		If EnumValues is empty, will return the maximum allowable value
			that can fit within the field's allotted bits.
		"""
		if len(cls.EnumValues) == 0:
			return cls.BIT_LENGTH_MAXIMUM
		return max([v.value for v in list(cls.EnumValues)])
	
	@classmethod
	def validate(cls, val):
		"""Checks for val within EnumValues and returns it if it exists.
			Otherwise uses IntField's validation mechanism.
			Notably this means that if a value is not defined in EnumValues,
				but could fit inside the field's allotted bits, it will pass
				validation.
				
		Returns
		-------
		int
			Returns the original value if it passes validation.
		"""
		try:
			return cls.EnumValues(val).value
		except ValueError:
			return super().validate(val)
				
	def enrich(self):
		"""Checks within EnumValues for the field's current value attribute
			 and returns the corresponding key string as a human-readable
			 value.
		
		Raises
		------
		ValueError
			If the current value is not found within EnumValues and does
				not pass IntField's validation function.
		
		Returns
		-------
		str | int
			If the field's value attribute exists within EnumValues,
				returns the key that corresponds to that value.
			Otherwise, returns the current value if it passes validation.
		"""
		try:
			return self.EnumValues(self.value).name
		except ValueError:
			return super().enrich()
		except AttributeError:
			return super().enrich()

class BitEnabledField(EnumField):
	"""Extends EnumField to provide bit-like functionality to indicate
		whether the bit enables a feature.
	
	A True value indicates that the field is enabled
	A False value indicates that the field is disabled
	"""
	
	BIT_LENGTH = 1
	
	class EnumValues(Enum):
		DISABLED = 0
		ENABLED  = 1
		
class BitDisabledField(EnumField):
	"""Extends EnumField to provide bit-like functionality to indicate
		whether the bit disables a feature.
	
	A False value indicates that the field is enabled
	A True value indicates that the field is disabled
	"""
	
	BIT_LENGTH = 1
	
	class EnumValues(Enum):
		ENABLED  = 0
		DISABLED = 1
	
class MaskField(IntField):
	"""Extends IntField so that its value acts as a bitmask.
	
	Implements all bitwise operations __and__, __or__, __xor__, __invert__,
	__lshift__, and __rshift__.
	
	Attributes
	----------
	Flags : enum.IntFlag
	bit_length : int
		The number of bits that make up the mask, including any reserved bits.
		
	Methods
	-------
	enrich()
		Returns a dictionary of all of the flag keys to a boolean value.
	"""
	
	class Flags(IntFlag):
		"""An enumeration intended to be overridden by child classes that
			defines keys corresponding to each of the mask's flags.
		"""
		pass
		
	@classmethod
	@property	
	def BIT_LENGTH(cls):
		return len(cls.Flags)
	
	def enrich(self):
		"""Returns a dictionary of all of the keys in Flags to a boolean value.
		
		Returns
		-------
		dict{str: bool}
		"""
		return {f.name: self.value & f.value != 0 for f in self.Flags}
	
	def __and__(self, val):
		return (self.value & val) & self.MASK
	
	def __or__(self, val):
		return (self.value | val) & self.MASK
			
	def __xor__(self, val):
		return (self.value ^ val) & self.MASK
	
	def __invert__(self):
		return (~self.value) & self.MASK
	
	def __lshift__(self, places):
		"""Left shifts the current value by a number of places and then truncates
			any bits that would fall outside of the defined flags.
		"""
		return (self.value << places) & bintools.get_mask(self.BIT_LENGTH)
	
	def __rshift__(self, places):
		"""Right shifts the current value by a number of places and then truncates
			any bits that would fall outside of the defined flags.
		"""
		return (self.value >> places) & bintools.get_mask(self.BIT_LENGTH)

class VariableLengthFlagField(MaskField, metaclass=MetaEnum):
	"""
	TODO, this currently does not work and is not used.
	"""
	FLAG_LENGTH = 1
	
	class EnumValues(Enum):
		pass
	
	@classmethod
	@property	
	def BIT_LENGTH(cls):
		return len(cls.Flags) * cls.FLAG_LENGTH
	
	def enrich(self):
		binary = bin(self.value)[2:]
		values = [int(binary[i:i+self.flag_length]) for i in range(0, len(binary), self.FLAG_LENGTH)]
		
		if len(self.EnumValues) > 0:
			return {f.name: self.EnumValues[values[i]] for (i, f) in enumerate(self.Flags)}
		else:	
			return {f.name: values[i] for (i, f) in enumerate(self.Flags)}
		
class StringField(Field):
	"""A class representing a string value stored in a field in a binary
		protocol block.
	
	Attributes
	----------
	value : str
	DEFAULT : str, default=""
	MAX_LENGTH : int, default=256
		Maximum number of bytes/characters that can be held within a field.
	ENCODING : str. default="latin-1"
		An encoding for converting between bytes and human-readable characters.
	bit_length : int
		The number of bits in the current string, capped at the MAX_LENGTH * 8.
		
	Methods
	-------
	validate(val) (classmethod)
		Ensures that the given string can be encoded into the field's prefered
			encoding and fits within the maximum number of bytes.
	"""
	DEFAULT = ""
	MAX_LENGTH = 256
	ENCODING = "latin-1"
	
	@property
	def bit_length (self):
		return min(self.MAX_LENGTH, len(self.value)) * 8

	@classmethod
	def validate(cls, val):
		"""Ensures a string can be packed to the field's encoding.
		
		Parameters
		----------
		val : str
			The string being validated.
			
		Raises
		------
		ValueError
			If the length of the string exceeds the max length of the field.
		UnicodeEncodeError
			If the string contains characters that can't be encoded.
			
		Returns
		-------
		str
			The original string provided if it passes validation.
		"""
		#will throw an exception if there are invalid characters
		encoded_string = val.encode(cls.ENCODING).decode()
		
		if len(encoded_string) <= cls.MAX_LENGTH:
			return encoded_string
		else:
			raise ValueError(f"{cls.__name__} string {encoded_string} (length={len(encoded_string)}) exceeds maximum string length of {cls.MAX_LENGTH}.")
	
	@classmethod
	def pack(cls, val):
		"""Does nothing except for validate and return the provided value.
		
		Required for implementing abstract parent class.
		"""
		return cls.validate(val)
	
	def enrich(self):
		"""Does nothing except for validate and return the current value.
		
		Required for implementing abstract parent class.
		"""
		return self.validate(self.value)
	
	@classmethod
	def from_bytes(cls, stream, length = None, null_terminated = False, consume = True):
		return bintools.get_string(stream = stream, length = length, null_terminated = null_terminated, consume = consume)
	
	def to_bytes(self, null_padded = False):
		return bintools.pack_string(self.value, max_length = self.MAX_LENGTH, null_padded = null_padded, encoding = self.ENCODING)
	
class TimeField(IntField):
	"""A class representing Blackline Safety's implementation of a timestamp.
	
	17 bits are used to store the number of seconds that have passed since
		midnight UTC.
	
	Attributes
	----------
	value : str
	bit_length = 17
	MAXIMUM = 24*60*60
		The number of seconds in a single day.
	EPOCH : datetime
		The date represented by a zero-value, 2010-01-01.
	TIME_FORMAT : String
		The format to print a timestamp, hh:mm:ss.
	
	Methods
	-------
	validate(val) (classmethod)
		Ensures that the given value can be parsed as a time and fits into
			the number of seconds in a given day.
	pack() : int
		Packs a human-readable timestamp into the number of seconds since
			midnight.
	enrich() : datetime
	"""
	BIT_LENGTH = 17
	
	MINIMUM = 0
	MAXIMUM = 24 * 60 * 60 # hours * minutes * seconds
	
	EPOCH = datetime(year = 2010, month = 1, day = 1)
	
	INVALID_TIME = 0x1FFFF
	TIME_FORMAT = "%H:%M:%S"
	
	@classmethod
	def validate(cls, val):
		"""A validation function for a time to potentially be assigned as the
			TimeField's value attribute.
			
		Parameters
		----------
		val : int | str
			If val is an int, treat it as the number of seconds since midnight.
			If val is str, treat it as a datetime with format TIME_FORMAT.
		
		Raises
		------
		OverflowError
			If the value is too small or too large to be contained within the
				allotted number of bits.
		ValueError
			If the value cannot be interpreted as a datetime with the specified
				TIME_FORMAT.
		TypeError
			If the value is neither an integer nor a string.
			
		Warns
		-----
		UserWarning
			If val exceeds the number of seconds in a day, but can still be
				stored in the allotted number of bits.
			
		Returns
		-------
		int
			Returns val if validation is successful.
		"""
		if isinstance(val, int):
			if val == cls.INVALID_TIME:
				return val
			if val < cls.BIT_LENGTH_MINIMUM or val > cls.BIT_LENGTH_MAXIMUM:
				error_string = f"{cls.__name__} value {val} cannot be contained within {cls.BIT_LENGTH} bits."
				raise OverflowError(error_string)
			if val < cls.MINIMUM or val > cls.MAXIMUM:
				warning_string = (f"{cls.__name__} has invalid number of seconds: {val} exceeds {cls.MAXIMUM} seconds.")
				#warnings.warn(warning_string, UserWarning)
				dbg.warning(warning_string)
			return val
		elif isinstance(val, str):
			datetime.strptime(val, cls.TIME_FORMAT)
			return val	
		else:
			raise TypeError(f"{cls.__name__} cannot parse time from {type(val).__name__}. Must be integer or datetime.time")
	
	@classmethod	
	def pack(cls, value):
		"""Packs a human-readable time into a number of seconds since midnight.
			
		Parameters
		----------
		val : str | datetime
			If val is a datetime, treat it as-is.
			If val is str, treat it as a datetime with format TIME_FORMAT.
		
		Raises
		------
		ValueError
			If the value cannot be interpreted as a datetime with the specified
				TIME_FORMAT.
		TypeError
			If the value is neither an datetime nor a string.
				
		Returns
		-------
		int
			The number of seconds since midnight.
		"""
		if isinstance(value, str):
			timestamp = datetime.strptime(value, cls.TIME_FORMAT) 
		elif isinstance(value, datetime):
			timestamp = value
		else:
			raise TypeError(f"{cls.__name__} cannot parse time from {type(value).__name__}. Must datetime.time or string formatted as {cls.TIME_FORMAT}.")
		
		# get the number of seconds between the value and the start of time
		delta = timestamp - datetime(0, 0, 0)
		seconds = delta.total_seconds()
		return seconds
	
	def enrich(self):
		"""Convert the stored value to a human-readable datetime.
				
		Returns
		-------
		string
			The stored time in hh:mm:ss format.
		"""
		if self.value == self.INVALID_TIME:
			return "INVALID_TIME"
		else:
			return (self.EPOCH + timedelta(seconds = self.value)).strftime(self.TIME_FORMAT)
	
class DateTimeField(TimeField):
	"""Extends TimeField to support a date as well as a time.
	
	17 bits are used to store the number of seconds that have passed since
		midnight UTC.
	15 bits are used to store the number of days since the epoch.
	
	Attributes
	----------
	value : str
	bit_length = 32
	TIME_BIT_LENGTH = 17
	DATE_BIT_LENGTH = 15
	MAX_TIME = 24*60*60
		The number of seconds in a single day.
	MAX_DATE = 0x7FFF
	MAXIMUM = 2099-09-18 23:59:59 
	EPOCH : datetime
		The date represented by a zero-value, 2010-01-01.
	TIME_FORMAT : String
		The format to print a datestamp, yyyy-mm-dd hh:mm:ss.
	
	Methods
	-------
	validate(val) (classmethod)
		Ensures that the given value can be parsed as a datetime and fits into
			32 bits..
	pack() : int
		Packs a human-readable datestamp into a 32-bit number where the bottom
			17 bits represent the number of seconds since midnight and the top
			15 bits represent the number of days since the epoch.
	enrich() : datetime
	"""
	TIME_BIT_LENGTH = TimeField.BIT_LENGTH
	DATE_BIT_LENGTH = 15
	
	BIT_LENGTH = DATE_BIT_LENGTH + TIME_BIT_LENGTH
	
	MIN_TIME = TimeField.MINIMUM
	MAX_TIME = TimeField.MAXIMUM
	MIN_DATE = 0
	MAX_DATE = sum([2 ** i for i in range(DATE_BIT_LENGTH)])
	
	TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
	TIME_MASK   = sum([2**i for i in range(TIME_BIT_LENGTH)])
	MINIMUM = 0
	MAXIMUM = (MAX_DATE << TIME_BIT_LENGTH) + MAX_TIME 
	
	@classmethod
	def validate(cls, val):
		"""A validation function for a time to potentially be assigned as the
			TimeField's value attribute.
			
		Parameters
		----------
		val : int | str
			If val is an int, treat it as a 32-bit number where:
				The bottom 17 bits are the number of seconds since midnight
				The top 15 bits are the number of days since the epoch
			If val is str, treat it as a datetime with format TIME_FORMAT.
		
		Raises
		------
		OverflowError
			If the date is too big to fit in the top 15 bits of the datetime.
		ValueError
			If the value cannot be interpreted as a datetime with the specified
				TIME_FORMAT.
		TypeError
			If the value is neither an integer nor a string.
			
		Warns
		-----
		UserWarning
			If the time exceeds the number of seconds in a day, but can still
				be stored in the allotted number of bits.
			
		Returns
		-------
		int
			Returns val if validation is successful.
		"""
		if isinstance(val, int):
			date    = val >> cls.TIME_BIT_LENGTH
			if date < cls.MIN_DATE or date > cls.MAX_DATE:
				error_string = f"{cls.__name__} date is too far in the future {val} cannot be translated as a {cls.BIT_LENGTH}-bit number of days."
				raise OverflowError(error_string)
			
			time = val & cls.TIME_MASK
			if time < cls.MIN_TIME or time > cls.MAX_TIME:
				warning_string = (f"{cls.__name__} has invalid number of seconds: {time} exceeds {cls.MAX_TIME} seconds.")
				#warnings.warn(warning_string, UserWarning)
				dbg.warning(warning_string)
			
			return val
		elif isinstance(val, datetime):
			if val < cls.EPOCH:
				raise ValueError(f"{cls.__name__} date {val.strftime(cls.TIME_FORMAT)} before supported epoch of {cls.EPOCH.strftime(cls.TIME_FORMAT)}.")
			if val > (cls.EPOCH + timedelta(days = cls.MAX_DATE, seconds = cls.MAX_TIME)):
				raise OverflowError(f"{cls.__name__} date {val.strftime(cls.TIME_FORMAT)} too far in the future.")
			return val
		elif isinstance(val, str):
			datetime.strptime(val, cls.TIME_FORMAT)
			return val	
		else:
			raise TypeError(f"{cls.__name__} is unable to parse time from {type(val).__name__} . Must be integer or datetime.datetime")
	
	@classmethod
	def pack(cls, value):
		"""Packs a human-readable datetime into a number of seconds since midnight
			and a number of days since the epoch.
			
		Parameters
		----------
		val : str | datetime
			If val is a datetime, treat it as-is.
			If val is str, treat it as a datetime with format TIME_FORMAT.
		
		Raises
		------
		ValueError
			If the value cannot be interpreted as a datetime with the specified
				TIME_FORMAT.
		TypeError
			If the value is neither an datetime nor a string.
				
		Returns
		-------
		int
			A 32-bit number where:
				The bottom 17 bits are the number of seconds since midnight
				The top 15 bits are the number of days since the epoch
		"""
		if isinstance(value, str):
			timestamp = datetime.strptime(value, cls.TIME_FORMAT) 
		elif isinstance(value, datetime):
			timestamp = value
		else:
			raise TypeError(f"{cls.__name__} is unable to parse time from {type(value).__name__}. Must datetime.time or string formatted as {cls.TIME_FORMAT}.")
		
		delta = timestamp - cls.EPOCH
		total_seconds = delta.total_seconds()
		days = int(total_seconds / cls.MAX_TIME)
		seconds = total_seconds - (days * cls.MAX_TIME)
		return (days << self.TIME_BIT_LENGTH) + seconds
	
	# can be overridden to provide enriched data
	def enrich(self):
		"""Convert the stored value to a human-readable datetime.
				
		Returns
		-------
		string
			The stored time in yyyy-mm-dd hh:mm:ss format.
		"""
		days    = self.value >> self.TIME_BIT_LENGTH
		seconds = self.value & self.TIME_MASK
		return (self.EPOCH + timedelta(days = days, seconds = seconds)).strftime(self.TIME_FORMAT)
	
class RawDataField(Field):
	"""A class representing a bytearray of raw data.
	
	Attributes
	----------
	value : bytearray
	DEFAULT = bytearray()
	MAX_LENGTH : int, default=1024
	
	Methods:
	--------
	enrich() : string
		Returns the saved bytearray data as a hex string.
	"""
	DEFAULT = bytearray()
	MAX_LENGTH = 1024
	
	@classmethod
	def validate(cls, val):
		"""A validation function for raw data to assure it does not exceed the
			maximum permitted length.
			
		Parameters
		----------
		val : bytearray
		
		Raises
		------
		OverflowError
			If the data exceeds the maximum permitted length.
			
		Returns
		-------
		bytearray
			Returns val if validation is successful.
		"""
		if len(val) > cls.MAX_LENGTH:
			raise OverflowError(f"{cls.__name__} cannot contain more than {cls.MAX_LENGTH} bytes of data.")
		return val
	
	@classmethod
	def pack(cls, val):
		"""Does nothing and simply returns the value. Required as an
			abstractmethod in parent class.
		"""
		return val
	
	def enrich(self):
		"""Returns the currently stored value as a hex string."""
		return self.value.hex()
	
	@classmethod
	def from_bytes(cls, stream, num_bytes = 1, consume = True):
		return bintools.get_bytes(stream, num_bytes = num_bytes, consume = consume)
	
	def to_bytes(self):
		return self.value

class BlockField(Field):
	"""A class representing an complex object stored in a field in a binary
		protocol block.
	
	Attributes
	----------
	value : ProtocolBlock
	DEFAULT = None
	bit_length : int
		Recursively calculate the length of the protocol block.
		
	Methods
	-------
	to_bytes() : bytearray
		Wraps the to_bytes() function in the stored protocol block.
	validate() : ProtocolBlock
		Ensures that an object is the correct type of block to store.
	"""
	DEFAULT = None
	TYPE    = ProtocolBlock
	
	@property
	def bit_length(self):
		"""Bit length cannot currently be calculated for a BlockField as
			its potential contents are too variable.
		"""
		raise NotImplementedError
	
	@classmethod	
	def validate(cls, value):
		"""Ensures that an object is the correct type of ProtocolBlock to store."""
		if not isinstance(value, cls.TYPE):
			raise TypeError(f"{cls.__name__}: Value type {type(value)} is not a {cls.TYPE.__name__}")
		return value
	
	@classmethod
	def pack(cls, val):
		"""Does nothing and simply returns the value. Required as an
			abstractmethod in parent class.
		"""
		return val
	
	def enrich(self):
		"""Returns a hash of the stored ProtocolBlock's fields"""
		return {k: f.enrich() for (k,f) in self.value.fields}
	
	@classmethod
	def from_bytes(cls, stream, num_bytes = 1, consume = True):
		return cls.from_bytes(stream)
	
	def to_bytes(self):
		return self.value.to_bytes()
	
class BlockListField(BlockField, Iterator):
	"""Extends BlockList to store a list of ProtocolBlocks of the same type.
		Is also considered an iterator over the stored ProtocolBlocks.
	
	Attributes
	----------
	value : list[ProtocolBlock]
	DEFAULT = []
	bit_length : int
		Recursively calculate the length of the protocol block.
		
	Methods
	-------
	to_bytes() : bytearray
		Converts all stored items to bytes and appends them.
	validate() : list[ProtocolBlock]
		Ensures that all objects are the correct type of block to store.
	"""
	DEFAULT = []
	TYPE    = list
	
	def __init__(self, field_type, *values):
		self.field_type = field_type
		self.value      = list(values)
	
	def __iter__(self):
		return self.value.__iter__()
	
	def __next__(self):
		return self.value.__next__()
	
	def validate(self, values):
		"""Ensures that all objects are the correct type of block to store.
		
		Parameters
		----------
		values : iterable
		"""
		for v in values:
			if not isinstance(v, self.field_type):
				raise TypeError(f"{type(self).__name__}: Value type {type(v).__name__} is not a {self.field_type.__name__}")
		return values
	
	@classmethod
	def from_bytes(stream):
		return self.TYPE.from_bytes(stream)
	
	def to_bytes(self):
		"""Converts all stored field values to bytes."""
		mybytes = bytearray()
		for f in self.value:
			mybytes += f.value.to_bytes()
		return mybytes
