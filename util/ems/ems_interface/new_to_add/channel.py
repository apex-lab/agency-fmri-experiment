from preset import Preset

class Channel:

    def __init__(self,channel,intensity,pulsewidth, name):
        self.channel_number_on_EMS_machine = channel
        self.intensity = intensity
        self.pulsewidth = pulsewidth
        self.name = name
        self.presets = []
    
    def set_channel(channel):
        self.channel_number_on_EMS_machine = channel

    def set_parameters(intensity, pulsewidth, name):
        self.channel_number_on_EMS_machine = channel
        self.intensity = intensity
        self.pulsewidth = pulsewidth
        self.name = str(name)

    def set_name(name):
        self.name = str(name)

    def add_preset(intensity, pulsewidth, preset_name):
        if search_preset(preset_name) == False:
            p = Preset(intensity, pulsewidth, preset_name)
            self.presets.append(p)
        else:
            print("Warning while adding preset: " + preset_name + " duplicate in Channel " + self.name + " , will not add again with same name.")

    def remove_preset(preset_name):
        if search_preset(preset_name) == True:
            self.presets.remove(preset_name)
        else:
            print("Warning while removing preset: " + preset_name + " not found in Channel " + self.name)

    def activate_preset(preset_name):
        if search_preset(preset_name) == True:
            self.intensity = p.intensity
            self.pulsewidth = p.pulse_width
            self.active_preset = preset_name 
        else:
            print("Warning while activating preset: " + preset_name + " not found in Channel " + self.name) 

    def set_intensity(intensity):
        self.intensity = intensity

    def set_pulsewidth(pulsewidth):
        self.pulsewidth = pulsewidth
