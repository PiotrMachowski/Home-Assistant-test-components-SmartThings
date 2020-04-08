from homeassistant.components.media_player import (
    MediaPlayerDevice,
    DEVICE_CLASS_SPEAKER,
)
from homeassistant.components.media_player.const import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_STOP,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP,
    SUPPORT_VOLUME_SET,
    SUPPORT_SHUFFLE_SET
)
from homeassistant.const import (
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_ON,
    STATE_OFF
)

from typing import Optional, Sequence

from pysmartthings import Attribute, Capability, DeviceEntity

from . import SmartThingsEntity
from .const import DATA_BROKERS, DOMAIN

CONTROLLABLE_SOURCES = ["bluetooth", "wifi"]

VALUE_TO_STATE = {
    "playing": STATE_PLAYING,
    "paused": STATE_PAUSED,
    "on": STATE_ON,
    "off": STATE_OFF,
    "unknown": None,
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add switches for a config entry."""
    broker = hass.data[DOMAIN][DATA_BROKERS][config_entry.entry_id]
    async_add_entities(
        [
            SmartThingsMediaPlayer(device)
            for device in broker.devices.values()
            if broker.any_assigned(device.device_id, MEDIA_PLAYER_DOMAIN)
        ]
    )


def get_capabilities(capabilities: Sequence[str]) -> Optional[Sequence[str]]:
    """Return all capabilities supported if minimum required are present."""
    min_required = [
        Capability.media_playback,
        Capability.switch,
    ]
    all_supported = [
        Capability.switch,
        Capability.audio_volume,
        Capability.media_playback_shuffle,
        Capability.media_input_source,
        Capability.audio_mute,
        Capability.media_playback,
    ]
    # Must have one of the min_required
    if any(capability in capabilities for capability in min_required):
        return all_supported
    return None


class SmartThingsMediaPlayer(SmartThingsEntity, MediaPlayerDevice):

    def __init__(self, device):
        """Initialize the media_player class."""
        super().__init__(device)
        self._media_device = MediaPlayerDeviceEntity(device)
        self._state = None
        self._state_attrs = None
        self._supported_features = SUPPORT_PLAY | SUPPORT_PAUSE | SUPPORT_STOP
        if Capability.audio_volume in device.capabilities:
            self._supported_features |= SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP
        if Capability.audio_mute in device.capabilities:
            self._supported_features |= SUPPORT_VOLUME_MUTE
        if Capability.switch in device.capabilities:
            self._supported_features |= SUPPORT_TURN_ON | SUPPORT_TURN_OFF
        if Capability.media_input_source in device.capabilities:
            self._supported_features |= SUPPORT_SELECT_SOURCE
        if Capability.media_playback_shuffle in device.capabilities:
            self._supported_features |= SUPPORT_SHUFFLE_SET

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._device.switch_off(set_status=True)
        # State is set optimistically in the command above, therefore update
        # the entity state ahead of receiving the confirming push updates
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._device.switch_on(set_status=True)
        # State is set optimistically in the command above, therefore update
        # the entity state ahead of receiving the confirming push updates
        self.async_schedule_update_ha_state()

    async def async_mute_volume(self, mute):
        if mute:
            await self._media_device.mute(set_status=True)
        else:
            await self._media_device.unmute(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_set_volume_level(self, volume):
        await self._media_device.set_volume(int(volume * 100), set_status=True)
        self.async_schedule_update_ha_state()

    async def async_volume_up(self):
        await self._media_device.volume_up(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_volume_down(self):
        await self._media_device.volume_down(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_play(self):
        await self._media_device.play(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_pause(self):
        await self._media_device.pause(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_stop(self):
        await self._device.stop(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_select_source(self, source):
        await self._media_device.set_input_source(source, set_status=True)
        self.async_schedule_update_ha_state()

    async def async_set_shuffle(self, shuffle):
        await self._media_device.set_playback_shuffle(shuffle, set_status=True)
        self.async_schedule_update_ha_state()

    @property
    def device_class(self):
        return DEVICE_CLASS_SPEAKER

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def media_title(self):
        if self.state in [STATE_PLAYING, STATE_PAUSED]:
            return self._media_device.media_title()
        return None

    @property
    def state(self):
        if self._device.status.switch:
            if self.source is not None and self.source in CONTROLLABLE_SOURCES:
                if self._media_device.playback_status() in VALUE_TO_STATE:
                    return VALUE_TO_STATE[self._media_device.playback_status()]
            return STATE_ON
        return STATE_OFF

    @property
    def is_volume_muted(self):
        if self.supported_features & SUPPORT_VOLUME_MUTE:
            return self._media_device.audio_mute()
        return None

    @property
    def volume_level(self):
        if self.supported_features & SUPPORT_VOLUME_SET:
            return self._media_device.audio_volume() / 100
        return None

    @property
    def source(self):
        if self.supported_features & SUPPORT_SELECT_SOURCE:
            return self._media_device.input_source()
        return None

    @property
    def source_list(self):
        if self.supported_features & SUPPORT_SELECT_SOURCE:
            return self._media_device.supported_input_sources()
        return None

    @property
    def shuffle(self):
        if self.supported_features & SUPPORT_SHUFFLE_SET:
            return self._media_device.playback_shuffle()
        return None


class MediaPlayerCommand:
    mute = 'mute'
    unmute = 'unmute'
    set_volume = 'setVolume'
    volume_up = 'volumeUp'
    volume_down = 'volumeDown'
    play = 'play'
    pause = 'pause'
    stop = 'stop'
    set_input_source = 'setInputSource'
    set_playback_shuffle = 'setPlaybackShuffle'


ATTRIBUTE_ON_VALUES = {
    Attribute.playback_shuffle: 'enabled'
}


class MediaPlayerDeviceEntity:

    def __init__(self, device: DeviceEntity):
        self._device = device

    def audio_mute(self) -> bool:
        return self._device.status.is_on(Attribute.mute)

    def audio_volume(self) -> int:
        return self._device.status.attributes[Attribute.volume].value

    def playback_status(self) -> str:
        return self._device.status.attributes[Attribute.playback_status].value

    def input_source(self) -> str:
        return self._device.status.attributes[Attribute.input_source].value

    def supported_input_sources(self) -> str:
        value = self._device.status.attributes[Attribute.supported_input_sources].value
        if "value" in value:
            return value["value"]
        return value

    def playback_shuffle(self) -> bool:
        return self._device.status.attributes[Attribute.playback_shuffle].value == ATTRIBUTE_ON_VALUES[
            Attribute.playback_shuffle]

    def media_title(self) -> bool:
        return self._device.status.attributes['trackDescription'].value

    async def mute(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.audio_mute, MediaPlayerCommand.mute)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.mute, 'muted')
        return result

    async def unmute(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.audio_mute, MediaPlayerCommand.unmute)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.mute, 'unmuted')
        return result

    async def set_volume(self, volume: int, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.audio_volume, MediaPlayerCommand.set_volume,
                                            [volume])
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.volume, volume)
        return result

    async def volume_up(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.audio_volume, MediaPlayerCommand.volume_up)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.volume, min(self.audio_volume() + 1, 100))
        return result

    async def volume_down(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.audio_volume, MediaPlayerCommand.volume_down)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.volume, max(self.audio_volume() - 1, 0))
        return result

    async def play(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.media_playback, MediaPlayerCommand.play)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.playback_status, 'playing')
        return result

    async def pause(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.media_playback, MediaPlayerCommand.pause)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.playback_status, 'paused')
        return result

    async def stop(self, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.media_playback, MediaPlayerCommand.stop)
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.playback_status, 'paused')
        return result

    async def set_input_source(self, source: str, set_status: bool = False, *, component_id: str = 'main') -> bool:
        result = await self._device.command(component_id, Capability.media_input_source,
                                            MediaPlayerCommand.set_input_source, [source])
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.input_source, source)
        return result

    async def set_playback_shuffle(self, shuffle: bool, set_status: bool = False, *,
                                   component_id: str = 'main') -> bool:
        shuffle_value = ATTRIBUTE_ON_VALUES[Attribute.playback_shuffle] if shuffle else 'disabled'
        result = await self._device.command(component_id, Capability.media_playback_shuffle,
                                            MediaPlayerCommand.set_playback_shuffle, [shuffle_value])
        if result and set_status:
            self._device.status.update_attribute_value(Attribute.playback_status, shuffle_value)
        return result
