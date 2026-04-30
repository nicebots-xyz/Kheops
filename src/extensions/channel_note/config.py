from pydantic import BaseModel


class ChannelNoteConfig(BaseModel):
    enabled: bool = True
    send_on_start: bool = True
