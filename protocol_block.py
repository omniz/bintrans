"""Base class definitions for ProtocolBlock objects designed to represent
	a de-serialized binary protocol object.

This file can be imported as a module and contains the following classes:

	* ProtocolBlock - the base class for all ProtocolBlock objects.

Author:      Zach High-Leggett

Created:     December 2023
Updated:     December 18, 2023
"""

from abc import abstractmethod
import json
from BinaryTranslator import bintools
import warnings
from BinaryTranslator import omnizdebug as dbg

class ProtocolBlock():
	"""A base class representing a deserialized binary protocol object.
	
	Attributes
	----------
	fields : dict{str : Field}
		A map from key strings to some field value representing a decoded
			value from within the binary message.
	TAB_SIZE : int, default=4
		The number of spaces to include when doing a JSON pretty print.
	
	Methods
	-------
	__str__() : str
		Returns a JSON pretty-print of the ProtocolBlock's fields as raw
			values with no unpacking.
	enrich() : str
		Returns a JSON pretty-print of the ProtocolBlock's fields unpacked
			into human-readable values.
	print_up_to_error() : void
		Replicates __str__() but will print as much of the output as possible
			before running into any errors.
	merge_int_fields : bytearray (static)
		A utility method to merge consecutive IntFields stored in the same
			ProtocolBlock.
	from_hex(str) : ProtocolBlock, (static)
		A utility method to convert a hex string to a bytearray and pass it
			to from_bytes().
	from_bytes(bytearray) : ProtocolBlock, (static, abstract)
		An abstract method that defines how to translate a binary bytearray
			data into the field values required by the protocol.
	to_bytes() : bytearray (abstract)
		An abstract method that defines how to translate field values into
			bytearray data required by the protocol.
	"""
	
	TAB_SIZE = 4
	
	_WARN_FOR_UNCLAIMED_KWARGS = False
	
	def __init__(self, **kwargs):
		"""Creates a ProtocolBlock object by initializing an empty field dict.
		
		Warns
		-----
		UserWarning
			If there are any keyword arguments that weren't consumed by a child
				class.
		"""
		self.fields = {}
		if len(kwargs) > 0 and self._WARN_FOR_UNCLAIMED_KWARGS:
			warning_string = f"{type(self).__name__} got unclaimed kwargs {kwargs}"
			#warnings.warn(warning_string, UserWarning)
			dbg.warning(warning_string)
			
	def __str__(self):
		"""Returns a JSON pretty-print of the ProtocolBlock's fields as raw
			values with no unpacking.
			
		Most values will either be integers, single-byte-encoded characters,
			another ProtocolBlock, or a list of ProtocolBlocks
		"""
		return json.dumps(self._get_object_dict(), indent = self.TAB_SIZE)
	
	def __repr__(self):
		return self.__str__()
	
	def enrich(self, **kwargs):
		"""Returns a JSON pretty-print of the ProtocolBlock's fields unpacked
			into human-readable values.
			
		Values may be converted based on expected units (ppm, degree Celsius,
			etc...) enum values, or individual mask bits.
		"""
		return json.dumps(self._enrich_object_dict(), indent = self.TAB_SIZE)
	
	def print_up_to_error(self, indent = 0):
		"""Replicates __str__() but will print as much of the output as possible
			before running into any errors.
		"""
		from BinaryTranslator.field import BlockField, BlockListField, Field
		
		# utility lambda for displaying variable spacing
		tabs = lambda x: " " * x * self.TAB_SIZE
		
		if isinstance(self, Field):
			print(tabs(indent+1) + str(self.value))
		else:
			print(tabs(indent) + "{")
			
			# go through all of the ProtocolBlock's fields
			for k, f in self.fields.items():
				
				# if a field contains a list of ProtocolBlocks, recurse on each one
				if isinstance(f, BlockListField):
					print(tabs(indent+1) + f"{k}: [")
					for i in f.value:
						i.print_up_to_error(indent = indent+2)
					print(tabs(indent+1) + "]")
					
				
				# if a field contains another ProtocolBlock, recurse
				elif isinstance(f, BlockField):
					print(tabs(indent+1) + f"{k}: " + "{")
					f.value.print_up_to_error(indent = indent+2)
					print(tabs(indent+1) + "}")
					
				
				# for any other field tyoes, print the key/value pair
				elif isinstance(f, Field):
					print(tabs(indent+1) + f"{k}:" + str(f.value))
					
				# for anything else, print a debug string (should never happen)
				else:
					print(tabs(indent+1) + f"{k}: {f} (unexpected {type(f).__name__})")
			print(tabs(indent) + "}")
		
	def _get_object_dict(self):
		"""Recursively builds a dictionary of all field values in the
			ProtocolBlock
		"""
		from BinaryTranslator.field import BlockField, BlockListField
		
		fields = {}
		for k, f in self.fields.items():
			if isinstance(f, BlockListField):
				fields[k] = [i._get_object_dict() for i in f]
			elif isinstance(f, BlockField):
				fields[k] = f.value._get_object_dict()
			else:
				fields[k] = f.value
		return fields
		
	def _enrich_object_dict(self):
		"""Recursively builds a dictionary of all field values in the
			ProtocolBlock in their enriched format.
		"""
		from BinaryTranslator.field import BlockField, BlockListField, ReservedField
		
		fields = {}
		for k, f in self.fields.items():
			if isinstance(f, ReservedField):
				continue
			elif isinstance(f, BlockListField):
				fields[k] = [i._enrich_object_dict() for i in f]
			elif isinstance(f, BlockField):
				fields[k] = f.value._enrich_object_dict()
			else:
				fields[k] = f.enrich()
		return fields
		#return {k: v.enrich() for k, v in o.__dict__.items() if isinstance(v, Field)}
	
	@classmethod
	def from_hex(cls, myhex, **kwargs):
		"""Passes a hex string to the ProtocolBlock's from_bytes() method."""
		return cls.from_bytes(bytearray.fromhex(myhex), **kwargs)
	
	@classmethod
	@abstractmethod
	def from_bytes(cls, mybytes, **kwrgs):
		"""Defines how the provided byte array can be converted to field values.
		
		Abstract method. Must be overridden by subclasses.
		
		Parameters
		----------
		mybytes : bytearray
		"""
		pass
	
	@abstractmethod
	def to_bytes(self, **kwargs):
		"""Defines how the stored field values can be converted to raw bytes.
		
		Abstract method. Must be overridden by subclasses.
		
		Returns
		-------
		bytearray
		"""
		return bytearray()
	
	@staticmethod
	def merge_int_fields(fields):
		"""A utility method to merge consecutive IntFields stored in the same
			ProtocolBlock based on their values and bitlengths.
			
		All values provided should be unsigned IntFields.
		"""
		return bintools.merge_bits([(f.value, f.bit_length) for f in fields])