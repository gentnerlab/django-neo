from django.db import models
from djorm_pgarray.fields import ArrayField
from model_utils.managers import InheritanceManager

# Models modeled after those in Neo.core

class NeoModel(models.Model):
    """ abstract base class for all Neo Models"""
    name = models.CharField(max_length=255,blank=True)
    description = models.TextField(blank=True)
    file_origin = models.CharField(max_length=255,blank=True) # use FileField() instead?

    objects = InheritanceManager()

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


# Lookup Tables
class Lookup(models.Model):
    """ abstract base class for all lookup tables """
    name = models.CharField(max_length=255,blank=False)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name   

    class Meta:
        abstract = True 

class EventType(Lookup):
    """ a type of event """
    def __unicode__(self):
        return self.name 

# Container Models
class NeoContainer(NeoModel):
    """ abstract base class for Neo Containers """
    file_datetime = models.DateTimeField(null=True,blank=True)
    rec_datetime = models.DateTimeField(null=True,blank=True)
    index = models.PositiveIntegerField(null=True,blank=True)

    class Meta(NeoModel.Meta):
        abstract = True

class Block(NeoContainer):
    """The top-level container gathering all of the data, discrete and continuous, for a given recording session. 
    Contains Segment and RecordingChannelGroup objects."""

    def list_units(self):
        pass
    def list_recordingchannels(self):
        pass

       
class Segment(NeoContainer):
    """A container for heterogeneous discrete or continous data sharing a common clock (time basis) but not 
    necessarily the same sampling rate, start time or end time. A Segment can be considered as equivalent 
    to a "trial", "episode", "run", "recording", etc., depending on the experimental context. May contain 
    any of the data objects """

    block = models.ForeignKey(Block,null=True,blank=True,db_index=True)

# Grouping Models
class NeoGroup(NeoModel):
    """ abstract base class for Neo Grouping Objects """
    class Meta(NeoModel.Meta):
        abstract = True

class RecordingChannelGroup(NeoGroup):
    """A group for associated RecordingChannel objects. 

    This has several possible uses:
    - for linking several AnalogSignalArray objects across several Segment objects inside a Block.
    - for multielectrode arrays, where spikes may be recorded on more than one recording channel, and so the 
        RecordingChannelGroup can be used to associate each Unit with the group of recording channels from which 
        it was calculated.
    - for grouping several RecordingChannel objects. There are many use cases for this. For instance, for intracellular 
        recording, it is common to record both membrane potentials and currents at the same time, so each 
        RecordingChannelGroup may correspond to the particular property that is being recorded. For multielectrode arrays, 
        RecordingChannelGroup is used to gather all RecordingChannel objects of the same array.
    """
    recordingchannels = models.ManyToManyField('RecordingChannel')

    def channel_names(self):
        """get names of associated recording channels"""
        pass
    def channel_indexes(self):
        """get indices of associated recording channels"""
        pass


class RecordingChannel(NeoGroup):
    """Links AnalogSignal, SpikeTrain objects that come from the same logical and/or physical channel inside a Block, 
    possibly across several Segment objects."""

    index = models.PositiveIntegerField(blank=False,null=False)

    x_coord = models.FloatField(null=True,blank=True)
    y_coord = models.FloatField(null=True,blank=True)
    z_coord = models.FloatField(null=True,blank=True)

    coord_units = models.CharField(max_length=255,)

    def coordinate(self): 
        """ TODO: might be better to define coordinate as a postgres array or make this return a Quantity

        """
        return (self.x_coord, self.y_coord, self.z_coord)

class Unit(NeoGroup):
    """A Unit gathers all the SpikeTrain objects within a common Block, possibly across several Segments, that have been 
    emitted by the same cell. A Unit is linked to RecordingChannelGroup objects from which it was detected.

    """
    block = models.ForeignKey(Block)
    recording_channel_group = models.ManyToManyField('RecordingChannelGroup')

# Data Models
class NeoData(NeoModel):
    """ abstract base class for Neo Containers """
    segment = models.ForeignKey(Segment,db_index=True)

    class Meta(NeoModel.Meta):
        abstract = True

class AnalogSignal(NeoData):
    """A regular sampling of a continuous, analog signal."""

    t_start = models.FloatField(default=0.0)
    signal = ArrayField(dbtype="float(53)",dimension=1) # array of double precision floats: [time]
    units = models.CharField(max_length=255,)

    sampling_period = models.FloatField(blank=False)
    sampling_period_units = models.CharField(max_length=255,blank=False)

    # dtype = models.CharField(max_length=255,blank=True)
    # copy = models.BooleanField(default=True)

    recording_channel = models.ForeignKey(RecordingChannel,null=True,blank=True)

    def sampling_rate(self):
        """ 1/sampling_period """
        return 1/self.sampling_period

    def duration(self):
        """ len(signal)*sampling_period """
        return float(len(self.signal))*self.sampling_period

    def t_stop(self):
        """ t_start + duration """
        return self.t_start + self.duration

    def __unicode__(self):
        return self.name

class AnalogSignalArray(NeoData):
    """A regular sampling of a multichannel continuous analog signal.


    not sure what to do with this... 

    I'm inclined to make this a ManyToManyField w/ AnalogSignal w/ a method that will generate 
    a numpy array on-the-fly.

    alternatively, Neo people were advocating making AnalogSignalArray the default and letting AnalogSignal be a 1D array.
    """
    
    analog_signals = models.ManyToManyField('AnalogSignal')


class IrregularlySampledSignal(NeoData):
    """A representation of a continuous, analog signal acquired at time t_start with a varying sampling interval."""

    recording_channel = models.ForeignKey(RecordingChannel)



class Spike(NeoData):
    """One action potential characterized by its time and waveform."""

    time = models.FloatField() # array of floats
    t_units = models.CharField(max_length=255,)

    waveforms = ArrayField(dbtype="float(53)",dimension=2) # array of double precision floats: [channel,time]
    sampling_rate = models.FloatField(null=True,blank=True)
    left_sweep = models.FloatField(null=True,blank=True)
    sort = models.BooleanField(default=False)

    unit = models.ForeignKey('Unit')

    def __unicode__(self):
        return self.time    

class SpikeTrain(NeoData):
    """A set of action potentials (spikes) emitted by the same unit in a period of time (with optional waveforms).

    """
    times = ArrayField(dbtype="float(53)",dimension=1) # array of double precision floats: [spike_time]
    t_start = models.FloatField(default=0.0)
    t_stop = models.FloatField()
    t_units = models.CharField(max_length=255,)

    waveforms = ArrayField(dbtype="float(53)",dimension=3) #  array of double precision floats: [spike,channel,time]
    sampling_rate = models.FloatField(null=True,blank=True)
    left_sweep = models.FloatField(null=True,blank=True)
    sort = models.BooleanField(default=False)

    def __unicode__(self):
        return len(self.times) 

# # alternatively we can define the relationship between Spikes & Spike Trains through Foreign Keys
# class Spike(NeoData):
#     """One action potential characterized by its time and waveform."""
#     time = models.FloatField() # array of floats
#     t_units = models.CharField(max_length=255,)

#     waveforms = ArrayField(dbtype="float(24)",dimension=2) # array of floats: [channel,time]
#     sampling_rate = models.FloatField(null=True,blank=True)
#     left_sweep = models.FloatField(null=True,blank=True)
#     sort = models.BooleanField(default=False)

#     spike_train = models.ForeignKey('SpikeTrainAlt',db_index=True)
#     def __unicode__(self):
#         return len(self.times)    

# class SpikeTrainAlt(NeoData):
#     """ alternative implementation of SpikeTrain """

#     t_start = models.FloatField(default=0.0)
#     t_stop = models.FloatField()

#     sort = models.BooleanField(default=False)

#     def times(self):
#         """ build an array of spike times from the times of the associated spikes"""
#         pass
#     def waveforms(self):
#         pass

class Event(NeoData):
    """A time point representng an event in the data"""
    time = models.FloatField()
    label = models.ForeignKey(EventType,db_index=True)

    def __unicode__(self):
        return "%s:%s" % (self.label,self.time)    

## these classes need some work

class EventArray(NeoData):
    """An array of Events

    I'm inclined to make this a ManyToManyField w/ Event w/ methods that will generate 
    the Neo-formatted attributes on-the-fly.
    """
    pass

class Epoch(Event):
    """An interval of time representing a period of time in the data """
    duration = models.FloatField()

class EpochArray(NeoData):
    """An array of Epochs

    I'm inclined to make this a ManyToManyField w/ Event w/ methods that will generate 
    the Neo-formatted attributes on-the-fly.

    """
    pass


