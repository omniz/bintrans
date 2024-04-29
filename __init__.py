"""Binary utility functions

This package provides several useful functions for dealing with binary data.

This file can be imported as a module and contains the following functions:

	* get_mask - Returns an n-length bit mask of all 1s.
	* peek_bytes - Returns the first n bytes of a bytearray without consuming
		them.
	* pop_bytes - Returns the first n bytes of a bytearray and removes them
		from the provided array object.
	* get_int - Returns an n-byte integer from the front of a bytearray.
	* get_string - Returns an n-character string from the front of a bytearray.
	* split_bits - Returns a list of int values from the front of a bytearray
		split into arbitrary bit lengths.
	* pack_partial_int - Returns a bytearray representing an int value
		packed into an n-bit integer potentially with an offset starting at a
		higher bit in the lowest byte. Mostly used by merge_bits() as a helper
		method.
	* pack_int - Returns a bytearray representing an int value packed into an
		n-byte value.
	* pack_string - Returns a bytearray representing a string value.

Author:      Zach High-Leggett

Created:     December 2023
Updated:     December 12, 2023
"""
import struct
import math
import sys
import warnings
import omnizdebug as dbg

def _order_bytes(mybytes, endianness):
	"""Orders a bytearray based on a given endianness.
	
	Parameters
	----------
	mybytes : bytearray
		A bytearray to be ordered.
	endiannness : str
		The desired byte order:
			* "little" if the first byte should be the least significant
			* "big" if the first byte should be the most significant
			
	Raises
	------
	NameError
		The endianness parameter is not a recognized value.
	
	Returns
	-------
	bytearray
		A copy of the original bytearray rearranged in the desired order.
	"""
	if endianness == "little":
		return mybytes[::-1]
	elif endianness == "big":
		return mybytes[::1]
	else:
		raise NameError(f"Unrecognized endianness {endianness}. Must be 'big' or 'little'.")

def _consumption_method(consume):
	"""Returns the proper function for getting bytes from the start of a
		bytearray based on whether or not we want to consume those bytes
		(ie: remove them from the front of the existing bytearray.
	
	Parameters
	----------
	consume : bool
		If True, returns the pop_bytes() method which will remove bytes
			from the provided bytelist as they are read.
		If False, returns peek_bytes() which will read bytes from the
			provided bytelist without removing them.
			
	Returns
	-------
		function
			The proper function for reading bytes based on the desired
				behaviour
	"""
	if consume:
		return pop_bytes
	else:
		return peek_bytes

def get_mask(num_bits, offset = 0):
	"""Returns an n-bit mask consisting of all 1s. Useful for generating
		masks intended to isolate a particular range of bits.
	
	Parameters
	----------
	num_bits : int
		The length of the desired bitmask.
	offset : int, default=0
		An optional number of 0s to append as the lower bits of the mask.
		
	Returns
	-------
	int
		The integer value of the resulting bitmask.
		
	Examples
	--------
	>>> get_mask(3)
	7
	>>> bin(get_mask(3))
	'0b111'
	
	>>> get_mask(5, 2)
	124
	>>> bin(get_mask(5, 2))
	'0b1111100'
	"""
	return sum([2**i for i in range(num_bits)]) << offset

def peek_bytes(stream, num=1):
	"""Reads bytes from the front of a bytearray without removing them.
	
	Parameters
	----------
	stream : bytearray
	num : int, default=1
		The number of bytes to read from the stream.
		
	Returns
	-------
	list
		A list containing the first n bytes of the provided array.
		
	Examples
	--------
	>>> b = bytearray.fromhex("ff")
	>>> b
	bytearray(b'\xff')
	>>> peek_bytes(b)
	[255]
	>>> b
	bytearray(b'\xff')
	
	>>> b = bytearray.fromhex("2d349c1a")
	>>> b
	bytearray(b'-4\x9c\x1a')
	>>> peek_bytes(b, 3)
	[45, 52, 156]
	>>> b
	bytearray(b'-4\x9c\x1a')
	"""
	return [stream[i] for i in range(num)]

def pop_bytes(stream, num=1):
	"""Reads and removes bytes from the front of a bytearray.
	
	Parameters
	----------
	stream : bytearray
	num : int, default=1
		The number of bytes to read from the stream.
		
	Returns
	-------
	list
		A list containing of the first n bytes of the provided
			bytearray.
		
	Examples
	--------
	>>> b = bytearray.fromhex("ff")
	>>> b
	bytearray(b'\xff')
	>>> pop_bytes(b)
	[255]
	>>> b
	bytearray(b'')
	
	>>> b = bytearray.fromhex("2d349c1a")
	>>> b
	bytearray(b'-4\x9c\x1a')
	>>> pop_bytes(b, 3)
	[45, 52, 156]
	>>> b
	bytearray(b'\x1a')
	"""
	return bytearray([stream.pop(0) for _ in range(num)])

def get_bytes(stream, num_bytes = 1, consume = True):
	return _consumption_method(consume)(stream, num_bytes)

def get_int(stream, num_bytes = 1, signed = False, consume = True, endianness = "little"):
	"""Parse an integer value from the front of a bytearray.
	
	Parameters
	----------
	stream : bytearray
	num_bytes : int, default=1
		The number of bytes to process 
	signed : bool, default=False
		If true, interpret the bytes read as an unsigned (non-negative) int.
		If flase, interpret the bytes read as a signed int.
	consume : bool, default=True
		If true, remove any bytes read from stream.
		If false, do not remove bytes read from stream.
	endianness : str, default="little"
		See order_bytes() for more information.
		
	Returns
	-------
	int
	"""
	mybytes = _consumption_method(consume)(stream, num_bytes)
	
	i = int.from_bytes(mybytes, byteorder = endianness, signed = signed)
	return i


def get_float(stream, consume = True, endianness = "little"):
	mybytes = _consumption_method(consume)(stream, 4)
	
	if endianness.lower() == "little":
		f = struct.unpack("<f", mybytes)
	elif endianness.lower() == "big":
		f = struct.unpack(">f", mybytes)
	else:
		raise NameError(f"Unrecognized endianness {endianness}. Must be 'big' or 'little'.")
		
	return f

# null terminated, no length -> read characters until NULL character encountered
# null terminated, X length -> read up to X characters, stop if NULL character encountered
# not null terminated, no length -> consume the rest of the stream
# not null terminated, X length -> read X characters
def get_string(stream, length = None, null_terminated = False, consume = True):
	"""Parse an integer value from the front of a bytearray.
	
	Parameters
	----------
	stream : bytearray
	length : int | None, default=None
		Specifies a maximum number of characters to read.
		If None, there is no upper bound on the number of characters being read.
	null_terminated : bool
		If True, stop reading bytes if a NULL byte (0x00) is found. The NULL
			byte will be included in the final string.
		If False, continue reading bytes even if a NULL byte (0x00) is found.
	consume : bool, default=True
		If true, remove any bytes read from stream.
		If false, do not remove bytes read from stream.
	
	Raises
	------
	IndexError
		If requested string length is not a positive integer.

	Returns
	-------
	string
	
	Examples
	--------
		
	>>> b = bytearray([65, 66, 67, 68, 0, 0, 90, 89, 88, 87])
	
	If length is not null and null_terminated is False, the specified
		number of bytes will be processed and returned.
	>>> s = get_string(b, length = 7, consume = False)
	>>> s
	'ABCDZ'
	>>> len(s)
	7
	
	If length is not null and null_terminated is True, bytes will be read
		until either a NULL byte is found, or the specified number of bytes
		have been processed.
		WARNING: 
	>>> s = get_string(b, length = 7, null_terminated = True, consume = False)
	>>> s
	'ABCD'
	>>> len(s)
	5
	
	If length is null and null_terminated is False, the remainder of the
		entire stream will be processed.
	>>> s = get_string(b, consume = False)
	>>> s
	'ABCDZYXW'
	>>> len(s)
	10
	
	If length is null and null_terminated is True, bytes will be read
		until a NULL byte is discovered. If no NULL byte is found, the
		remainder of the stream will be processed and returned as a string.
	>>> s = get_string(b, null_terminated = True, consume = False)
	>>> s
	'ABCD'
	>>> len(s)
	5
	"""
	if length is not None and length < 0:
		raise IndexError("Invalid string length " + str(length) + ". Non-negative integer expected.")
	
	# make a copy of the stream if we are not consuming it
	if not consume:
		stream = stream.copy()
	
	# append characters to a string until a NULL character is hit or the max length is reached
	mystring = ""
	while len(stream) > 0:
		new_char = get_int(stream)
		mystring += chr(new_char)
		if length is not None and len(mystring) >= length:
			break
		if null_terminated and new_char == 0:
			break
		
	return mystring

def split_bits(stream, *slice_lengths, consume = True, endianness = "little"):
	"""Retrieve bytes from the start of a bytearray and slice them into
		integers of a given number of bitlengths.
		
	Works by splitting the stream into n-bit segments for n in a given slice
		length. Segments will be further sub-divided anywhere a byte boundary
		is crossed. The resulting sub-segments will be recombined based on
		the endianness parameter into an n-bit integer.
		
	Examples
	--------
	Given the following bytearray:
	
	                /         byte0 (0xCB)          /        byte1  (0cDF)         /
	               | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	               |-------------------------------|-------------------------------|
	               | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
	 slice_lengths |---------------------------------------------------------------|
	 [8,8]         |           203                 |        223                    |
	 [1,15]        | 1 |       105                 |        223                    |
	    (little)   | 1 |                       32233                               |
	    (big)      | 1 |                       53755                               |
	 [5,3,7,1]     |           19      |     6     |        123                | 1 |
	 [4,7,5]       |        3      |       13      |     3    |          31        |
	    (little)   |        3      |            61            |          31        |
	    (big)      |        3      |           107            |          31        |
	 [4,4,6]       |        3      |       13      |        59            |  lost  |
	
		
	>>>split_bits(stream, 8, 8)
	[203, 223]
	>>splitbits(stream, 1, 15)
	[1, 32233]
	>>splitbits(stream, 1, 15, endianness = "big")
	[1, 53755]
	>>splitbits(stream, 5, 3, 7, 1)
	[19, 6, 123, 1]
	>>splitbits(stream, 4, 7, 5)
	[3, 61, 31]
	>>splitbits(stream, 4, 7, 5, endianness = "big")
	[3, 107, 31]
	>>splitbits(stream, 4, 4, 6)
	BytesWarning: Total bits requested 14 does not consume a full number of bytes, 2 bits will be dropped.
	[3, 13, 59]
		
	Parameters
	----------
	stream : bytearray
	*slice_lengths : [int]
		Specifies the bitlengths of the desired integers. The number of values
			returned will be equal to len(slice_lengths).
	consume : bool, default=True
		If true, remove any bytes read from stream.
		If false, do not remove bytes read from stream.
	endianness : str, default="little"
		See order_bytes() for more information. Endianness is only used for
			values which cross a byte boundary.
		
	Raises
	------
	OverflowError
		If requested more bits than are available in the stream.
	
	Warns
	-----
	BytesWarning
		If the number of bits requested does not consume a full number of
			bytes. ANY BITS REMAINING WILL BE DISCARDED FROM THE RETURN
			VALUE, even if consume is False.
	
	Returns
	-------
	[int]
		A list of n-bit integers, where n is the value at the corresponding
			index within *slice_lengths.
	"""
	
	bits_requested = sum(slice_lengths)
	bytes_required = math.ceil(bits_requested / 8)
	bytes_provided = len(stream)
	
	# throw an error if the caller requests more slices than there are bits available
	if bytes_required > bytes_provided:
		raise OverflowError(f"Requested {bits_requested} bits but only provided {bytes_provided} bytes ({stream}).")
	# print a warning if bits will be lost from a requested byte
	if bits_requested % 8 != 0:
		warning_string = f"Total bits requested {bits_requested} does not consume a full number of bytes, {8 - (bits_requested % 8)} bits will be dropped."
		#warnings.warn(warning_string, BytesWarning)
		dbg.warning(warning_string)
	
	# read the bytes required to fulfill the requested slice lengths
	mybytes = _consumption_method(consume)(stream, bytes_required)
	
	# initialize an empty array of sliced values
	slices = []
	
	# initialize a byte to pull bits from
	working_byte = None
	working_byte_bits_consumed = 0
	
	for slice_length in slice_lengths:
		segments = []
		slice_bits_consumed = 0
		while slice_bits_consumed < slice_length:
			# if working byte has been exhausted, get a new one
			if working_byte_bits_consumed == 0:
				working_byte = mybytes.pop(0)
				working_byte_bits_consumed = 0
					
			# get the number of bits still needed for the slice and the number of bits remaining in the working byte
			slice_bits_remaining = slice_length - slice_bits_consumed
			working_bits_remaining = 8 - working_byte_bits_consumed
			
			# get the number of bits needed for the next segment of the current slice
			capped_slice_length = min(slice_bits_remaining, working_bits_remaining)
			
			# get a mask of a number of 1s equal to the capped slice length
			mask = get_mask(capped_slice_length)
			
			# create a segment consisting of a value and the number of bits it represents
			segment = (working_byte & mask, capped_slice_length)
			segments.append(segment)
			
			# increment the number of bits consumed within the working byte
			slice_bits_consumed += capped_slice_length
			working_byte_bits_consumed = (working_byte_bits_consumed + capped_slice_length) % 8
			working_byte >>= capped_slice_length
			
		# combine all segments into a single slice value based on endianness
		myslice = 0
		for v, n in _order_bytes(segments, endianness):
			myslice <<= n
			myslice += v
		slices.append(myslice)
	return slices

def pack_partial_int(value, num_bits = 8, signed = False, endianness = "little", offset = 0):
	"""Pack an integer into a bytearray but add an n-bit offset to the first
		byte. Used to pack values that share a byte with another value or with
		a length which does not terminate at a byte boundary.
	
	Parameters
	----------
	value : int
	num_bits : int, default=8
	signed : bool, default=False
		If true, pack the value as an unsigned (non-negative) int.
		If false, pack the value as a signed int.
	endianness : str, default="little"
		See order_bytes() for more information.
	offset : int, default=0
		Pad the first byte by a number of 0 bits.
	
	Raises
	------
	OverflowError
		If value is too large to fit into the specified number of bytes.
	
	Returns
	-------
	bytearray
	"""
	value <<= offset
	
	bits_needed = num_bits + offset
	if bits_needed < 1 or value.bit_length() > bits_needed:
		raise OverflowError(f"Cannot pack integer {value} into {num_bits} bits with {offset}-bit offset.")
	
	mybytes = value.to_bytes(math.ceil(bits_needed / 8), byteorder = endianness, signed = signed)
	return mybytes

def pack_int(value, num_bytes = 1, signed = False, endianness = "little"):
	"""Pack an integer into an n-byte bytearray.
	
	Works as a shorthand for pack_int_partial() if:
		1) num_bits is divisible by 8, and
		2) offset is 0
	
	Parameters
	----------
	value : int
	num_bytes : int, default=1
	signed : bool, default=False
		If true, pack the value as an unsigned (non-negative) int.
		If false, pack the value as a signed int.
	endianness : str, default="little"
		See order_bytes() for more information.
	
	Raises
	------
	OverflowError
		If value is too large to fit into the specified number of bytes.
	
	Returns
	-------
	bytearray
	"""
	if num_bytes < 1 or value.bit_length() > num_bytes * 8:
		raise OverflowError(f"Cannot pack integer {value} into {num_bytes} bytes.")
	
	mybytes = value.to_bytes(num_bytes, byteorder = endianness, signed = signed)
	return mybytes

def pack_float(value, endianness = "little"):
	if endianness.lower() == "little":
		f = struct.pack("<f", value)
	elif endianness.lower() == "big":
		f = struct.unpack(">f", value)
	else:
		raise NameError(f"Unrecognized endianness {endianness}. Must be 'big' or 'little'.")
		
	return f

def pack_string(value, max_length = None, null_padded = False, encoding = "latin-1"):
	"""Pack a string into an n-byte bytearray.
	
	Parameters
	----------
	value : int
	max_length : int | None, default=None
		If None, pack the string into however many bytes are required.
		If set to some value, an error will be raised if the the given
			string is too long to fit in the allowed space.
	null_padded : bool, default=False 
		If True:
			If max_length is None, does nothing.
			If max_length is set to some value, appends NULL bytes to
				the value up to max_length characters.
		If False:
			Does nothing.
	encoding : str, default="latin-1"
		The text encoding used to pack the string value into the bytearray.
			Uses "latin-1" by default so that each character is one byte.
	
	Raises
	------
	OverflowError
		If value contains more than max_length characters.
	
	Returns
	-------
	bytearray
	"""
	if max_length is not None:
		if len(value) > max_length:
			raise OverflowError(f"Cannot pack {len(value)}-length string \"{value}\" into {max_length} bytes.")
		elif null_padded:
			value += chr(0) * (max_length - len(value))
					
	return value.encode(encoding)

def merge_bits(values, endianness = "little"):
	"""Pack a series of values into a bytearray, treating each value as an
		n-bit integer for some n specified for each value.
	
	If the total number of bits does not equal a full number of bytes, the
		remaining upper bits of the last byte will be 0.
	
	Parameters
	----------
	values : [tuple]
		A list of tuples (value, length) where:
			value : int
				An integer value to be packed into the resulting bytearray.
			length : int
				The number of bits to pack value into.
	endianness : str, default="little"
		See order_bytes() for more information.
	
	Warns
	-----
	BytesWarning
		If the total number of bits does not equal a full number of bytes.
	
	Returns
	-------
	bytearray
	"""
	# print a warning if bits will be lost from a requested byte
	bits_to_pack = sum([l for (_, l) in values])
	if bits_to_pack % 8 != 0:
		warning_string = f"Total bits to pack {bits_to_pack} does not occupy a full number of bytes, padding with {8 - (bits_to_pack % 8)} 0-bits."
		#warnings.warn(warning_string, BytesWarning)
		dbg.warning(warning_string)
	
	mybytes = bytearray()
	for i, (value, length) in enumerate(values):
		offset = (sum([l for (_, l) in values[0:i]])) % 8
		
		new_bytes = pack_partial_int(value, length, endianness = endianness, offset = offset)
		if offset != 0:
			# if the value isn't being packed at the  start of a byte boundary
			# bitwise-and the first byte of the newly packed value
			# with the last byte of the bytearray
			mybytes[-1] |= new_bytes[0]
			
			# append the remaining bytes to the bytearray
			if len(new_bytes) > 1:
				mybytes.extend(new_bytes[1:])
		else:
			# if the value is being packed at the start of a byte boundary
			# simply append the new bytes to the existing bytearray
			mybytes.extend(new_bytes)
	return mybytes