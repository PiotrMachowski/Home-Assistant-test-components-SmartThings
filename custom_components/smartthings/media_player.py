from typing import Optional, Sequence

from pysmartthings import Capability, DeviceEntity

from homeassistant.components.media_player import (
    MediaPlayerEntity,
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


class SmartThingsMediaPlayer(SmartThingsEntity, MediaPlayerEntity):

    def __init__(self, device: DeviceEntity):
        """Initialize the media_player class."""
        super().__init__(device)
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
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._device.switch_on(set_status=True)
        # State is set optimistically in the command above, therefore update
        # the entity state ahead of receiving the confirming push updates
        self.async_schedule_update_ha_state()

    async def async_mute_volume(self, mute):
        if mute:
            await self._device.mute(set_status=True)
        else:
            await self._device.unmute(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_set_volume_level(self, volume):
        await self._device.set_volume(int(volume * 100), set_status=True)
        self.async_schedule_update_ha_state()

    async def async_volume_up(self):
        await self._device.volume_up(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_volume_down(self):
        await self._device.volume_down(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_play(self):
        await self._device.play(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_pause(self):
        await self._device.pause(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_media_stop(self):
        await self._device.stop(set_status=True)
        self.async_schedule_update_ha_state()

    async def async_select_source(self, source):
        await self._device.set_input_source(source, set_status=True)
        self.async_schedule_update_ha_state()

    async def async_set_shuffle(self, shuffle):
        await self._device.set_playback_shuffle(shuffle, set_status=True)
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
            return self._device.status.attributes['trackDescription'].value
        return None

    @property
    def state(self):
        if self._device.status.switch:
            if self.source is not None and self.source in CONTROLLABLE_SOURCES:
                if self._device.status.playback_status in VALUE_TO_STATE:
                    return VALUE_TO_STATE[self._device.status.playback_status]
            return STATE_ON
        return STATE_OFF

    @property
    def is_volume_muted(self):
        if self.supported_features & SUPPORT_VOLUME_MUTE:
            return self._device.status.mute
        return None

    @property
    def volume_level(self):
        if self.supported_features & SUPPORT_VOLUME_SET:
            return self._device.status.volume / 100
        return None

    @property
    def source(self):
        if self.supported_features & SUPPORT_SELECT_SOURCE:
            return self._device.status.input_source
        return None

    @property
    def source_list(self):
        if self.supported_features & SUPPORT_SELECT_SOURCE:
            return self._device.status.supported_input_sources
        return None

    @property
    def shuffle(self):
        if self.supported_features & SUPPORT_SHUFFLE_SET:
            return self._device.status.playback_shuffle
        return None

    @property
    def should_poll(self) -> bool:
        return True

    async def async_update(self):
        await self._device.command('main', 'refresh', 'refresh')
