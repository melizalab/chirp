# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
audio:    module for i/o etc of audio data

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-07-29
"""
import os
import numpy as nx
import wave

class pcmfile(object):
    """
    Base class for pcm data containers. The most basic PCM container
    stores monaural data as binary samples, with no header metaddata.
    Subclasses dealing with more complex containers should alter these
    methods as necessary:

    nentries:     the number of entries in the file
    __iter__():    the indices of the entries in the file
    entry:         the current entry (writable if the container supports multiple entries)
    nframes:       number of frames in the current entry (long integer; read-only)
    nchannels:     number of channels in the current entry
    channels:      names of channels in the current entry
    sampling_rate: the number of frames per second of the current entry (float; read-only)
    timestamp:     the start time of the entry, in seconds since Jan 1, 1970
    dtype:         the storage type of the data
    read(chan):    retrieve data from the current entry as a numpy array
    write(data):   write samples to the current entry

    ================
    PCM implementation notes

    Information about the sampling rate or bit depth must be
    supplied to the initializer.  This implementation supports linear
    PCM encoding with 8,16, or 32-bit samples, specified as follows:
        'b':  8-bit
        'h':  16-bit
        'f':  32-bit

    PCM files do not store internal timestamp data, so the timestamp
    property returns the *modification* time of the file. The class
    will set this when the file is closed (when opened in write mode).
    """

    def __init__(self, filename, mode='r', sampling_rate=None, dataformat='h'):
        self._fname = filename
        self.fp = open(filename, mode+'b')
        self._mode = mode
        self._dtype = nx.dtype(dataformat)
        self._sampling_rate = sampling_rate
        if mode=='r':
            self._timestamp = float(os.fstat(self.fp.fileno()).st_mtime)
        else:
            self._timestamp = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return exc_val

    @property
    def filename(self):
        """ The path of the pcm file """
        return self._fname

    def close(self):
        """ Close the file handle; optionally setting the modification/access time """
        if hasattr(self,'fp') and hasattr(self.fp,'close'): self.fp.close()
        if self._mode!='r' and self._timestamp is not None:
            os.utime(self._fname, (self._timestamp, self._timestamp))

    def __iter__(self):
        yield 0

    @property
    def nentries(self):
        return 1

    def __get_entry(self):
        """ The current entry """
        return 0
    def __set_entry(self, value):
        if value != 0: raise ValueError, "Container can only hold one entry"
    entry = property(__get_entry, __set_entry)

    @property
    def nframes(self):
        """ The number of frames in the sound file.  """
        pos = self.fp.tell()
        self.fp.seek(0,2)
        bytes = self.fp.tell()
        self.fp.seek(pos,0)
        return bytes / self._dtype.itemsize

    @property
    def nchannels(self):
        """ The number of channels in the current entry """
        return 1

    @property
    def channels(self):
        """ The names of the channels in the current entry """
        return ('pcm',)

    def __get_sampling_rate(self):
        return self._sampling_rate
    def __set_sampling_rate(self, value):
        self._sampling_rate = value
    sampling_rate = property(__get_sampling_rate,__set_sampling_rate,
                             doc="The sampling rate of the current entry (in samples/second)")

    def __get_timestamp(self):
        return self._timestamp
    def __set_timestamp(self, value):
        self._timestamp = value
    timestamp = property(__get_timestamp, __set_timestamp,
                        doc=" The start time of the current entry, in seconds since Jan 1, 1970 ")

    def __get_dtype(self):
        return self._dtype
    def __set_dtype(self, value):
        self._dtype = nx.dtype(value)
    dtype = property(__get_dtype,__set_dtype)

    def read(self, frames=None, chan=None, memmap=False):
        """
        Return contents of file, starting at the beginning.

        frames: number of frames to return. None for all the frames in the file
        chan:   read specific channel (ignored by pcmfile)
        memmap: if True, returns a memmap to the file. Useful for
                large files that don't need to be read into memory all
                at once.
        """
        self.fp.seek(0,0)
        if frames:
            frames = min(frames, self.nframes)
        else:
            frames = self.nframes

        if memmap:
            return nx.memmap(self.fp, dtype=self._dtype, mode='c', shape=None)
        else:
            return nx.fromfile(self.fp, dtype=self._dtype, count=frames)

    def write(self, data):
        """
        Write data to end of file. Not supported for files opened in
        read-only mode.

        data: input data, in any form that can be converted to an
              array with an appropriate data type.
        """
        self.fp.seek(0,2)
        data = nx.asarray(data, self._dtype)
        data.tofile(self.fp, sep="")


class wavfile(pcmfile):
    """
    Class for reading WAV files to numpy arrays and writing numpy
    arrays to WAV files.

    WAV files support arbitrary sampling_rates and several data
    precisions. This class supports linear PCM encoding with 8,16,or
    32 bit samples. Bitdepth is detected automatically when opening
    files for reading; when opening files for write, specify the bit depth
    using the following codes:
        'b':  8-bit
        'h':  16-bit
        'f':  32-bit

    WAV files can be stereo or mono.  Writing stereo data is not
    supported.  Stereo data is returned as an Nx2 array, as a 1D array
    if accessed by channel name (see read()).

    WAV files do not store internal timestamp data, so the timestamp
    property returns the *modification* time of the file. The class
    cannot modify this value with any degree of confidence, since
    closing the file handle usually results in a flush operation.
    """
    _formatdict = {1:'b',2:'h',4:'f'}

    def __init__(self, filename, mode='r', sampling_rate=20000, dataformat='h'):
        self._fname = filename
        self._mode = mode
        self.fp = wave.open(filename, mode)
        dtype = nx.dtype(dataformat)
        if mode=='r':
            precision = self.fp.getsampwidth()
            if precision not in self._formatdict.keys():
                raise NotImplementedError, "Unable to handle wave files with sample width %d" % precision
            self._timestamp = float(os.fstat(self.fp.getfp().file.fileno()).st_mtime)
        else:
            self.fp.setparams((1, dtype.itemsize, sampling_rate, 0, "NONE", "not compressed"))
            self._timestamp = None

    @property
    def nframes(self):
        return self.fp.getnframes()

    def __get_sampling_rate(self):
        return self.fp.getframerate()
    def __set_sampling_rate(self, value):
        self.fp.setframerate(value)
    sampling_rate = property(__get_sampling_rate,__set_sampling_rate,
                             doc="The sampling rate of the current entry (in samples/second)")

    @property
    def nchannels(self):
        return self.fp.getnchannels()

    @property
    def channels(self):
        if self.nchannels == 1: return ('pcm',)
        else: return ('left','right')

    def __get_dtype(self):
        return nx.dtype(self._formatdict[self.fp.getsampwidth()])
    def __set_dtype(self, value):
        self.fp.setsampwidth(nx.dtype(value).itemsize)
    dtype = property(__get_dtype,__set_dtype)

    def read(self, frames=None, chan=None):
        """
        Return contents of WAV file. Not supported for files opened in write mode.

        frames: number of frames to return. None for all the frames in the file
        chan:   select a specific channel to read (see channels property)
        """
        if not isinstance(self.fp, wave.Wave_read):
            raise TypeError, "file opened for writing only"

        if frames:
            frames = min(frames, self.nframes)
        else:
            frames = self.nframes

        self.fp.rewind()
        S = nx.fromstring(self.fp.readframes(frames), dtype=self.dtype)
        if self.nchannels > 1:
            S = S.reshape((S.size/2, 2))
            if chan is None: return S
            elif chan == 'left': return S[:,0]
            elif chan == 'right': return S[:,1]
            else: raise ValueError, "%s is not a valid channel name" % chan
        else:
            return S

    def write(self, data):
        """
        Write data to the WAV file. Not supported for files opened in read mode.

        data: input data, in any form that can be converted to an
              array with an appropriate data type.
        """
        if not isinstance(self.fp, wave.Wave_write):
            raise TypeError, "file opened for reading only"
        bitdepth = self.fp.getsampwidth()
        dtype = nx.dtype(self._formatdict[bitdepth])
        data = nx.asarray(data, dtype)
        assert data.ndim == 1, "only mono files are supported"
        self.fp.writeframes(data.tostring())


try:
    import pyaudio
    _chunksize = 1024

    def play_wave(signal, Fs):
        p = pyaudio.PyAudio()
        stream = p.open(format = p.get_format_from_width(signal.dtype.itemsize),
                        channels = 1,
                        rate = int(Fs * 1000),
                        output = True)
        stream.write(signal.tostring())
        stream.stop_stream()
        stream.close()
        p.terminate()
except ImportError:
    def play_wave(signal, Fs):
        print "Unable to import pyaudio; playback not supported"


# Variables:
# End:
