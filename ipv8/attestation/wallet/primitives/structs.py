import struct

from .cryptosystem.value import FP2Value


def _num_to_str(num):
    """
    Convert an integer to a str.
    """
    out = b''
    h = hex(num)[2:]
    if h.endswith('L'):
        h = h[:-1]
    if (len(h) % 2) == 1:
        h = '0' + h
    for b in range(0, len(h), 2):
        out += struct.pack(">B", int(h[b] + h[b+1], 16))
    return out


def _str_to_num(s):
    """
    Convert a str to an integer.
    """
    out = 0
    for b in s:
        out <<= 8
        out |= struct.unpack(">B", b)[0]
    return out


def _pack(num):
    """
    Serialize an integer.
    """
    pnum = _num_to_str(num)
    l = len(pnum)
    return _num_to_str(l) + pnum


def _unpack(s):
    """
    Unserialize an integer from a str.
    """
    l = struct.unpack(">B", s[0])[0]
    return _str_to_num(s[1:l+1]), s[l+1:]


def pack_pair(a, b):
    """
    Serialize a pair of two integers.
    """
    return _pack(a) + _pack(b)


def unpack_pair(s):
    """
    Unserialize a pair of two integers.
    """
    a, r = _unpack(s)
    b, r = _unpack(r)
    return a, b, r


class BonehPublicKey(object):
    """
    A public key for Boneh et al.'s cryptosystem.
    """

    def __init__(self, n, p, g, h):
        self.n = n
        self.p = p
        self.g = g
        self.h = h

    def serialize(self):
        return _pack(self.n) + _pack(self.p) + _pack(self.g.a) + _pack(self.g.b) + _pack(self.h.a) + _pack(self.h.b)

    @classmethod
    def unserialize(cls, s, force_public=False):
        rem = s
        nums = []
        while rem:
            unpacked, rem = _unpack(rem)
            nums.append(unpacked)
        inits = [nums[0],
                 nums[1],
                 FP2Value(nums[1], nums[2], nums[3]),
                 FP2Value(nums[1], nums[4], nums[5])]
        if not force_public and len(nums) > 5:
            inits.append(nums[6])
        return cls(*inits)


class BonehPrivateKey(BonehPublicKey):
    """
    A private key for Boneh et al.'s cryptosystem.
    """

    def __init__(self, n, p, g, h, t1):
        super(BonehPrivateKey, self).__init__(n, p, g, h)
        self.t1 = t1

    def serialize(self):
        return super(BonehPrivateKey, self).serialize() + _pack(self.t1)

    def public_key(self):
        return BonehPublicKey(self.n, self.p, self.g, self.h)


class BitPairAttestation(object):
    """
    An attestation of a single bitpair of a larger Attestation.
    """

    def __init__(self, a, b, complement):
        self.a = a
        self.b = b
        self.complement = complement

    def compress(self):
        return self.a * self.b * self.complement

    def serialize(self):
        return _pack(self.a.a) + _pack(self.a.b) + _pack(self.b.a) + _pack(self.b.b) +\
               _pack(self.complement.a) + _pack(self.complement.b)

    @classmethod
    def unserialize(cls, s, p):
        rem = s
        nums = []
        while rem and len(nums) < 6:
            unpacked, rem = _unpack(rem)
            nums.append(unpacked)
        inits = [FP2Value(p, nums[0], nums[1]),
                 FP2Value(p, nums[2], nums[3]),
                 FP2Value(p, nums[4], nums[5])]
        return cls(*inits)


class Attestation(object):
    """
    An attestation for a public key of a value consisting of multiple bitpairs.
    """

    def __init__(self, PK, bitpairs):
        self.bitpairs = bitpairs
        self.PK = PK

    def serialize(self):
        out = ""
        out += self.PK.serialize()
        for bitpair in self.bitpairs:
            out += bitpair.serialize()
        return out

    @classmethod
    def unserialize(cls, s):
        PK = BonehPublicKey.unserialize(s, True)
        bitpairs = []
        rem = s[len(PK.serialize()):]
        while rem:
            attest = BitPairAttestation.unserialize(rem, PK.p)
            bitpairs.append(attest)
            rem = rem[len(attest.serialize()):]
        return cls(PK, bitpairs)
