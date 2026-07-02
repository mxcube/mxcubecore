import logging
from abc import abstractmethod
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

try:
    import argussight.grpc.argus_service_pb2 as pb2
    import argussight.grpc.argus_service_pb2_grpc as pb2_grpc
except ImportError:
    logging.getLogger("HWR").warning(
        "Cannot use Argus hardware object because argussight is not installed",
    )
    pass


class BaseAction(BaseModel):
    type: str = Field(
        description="Type of the action",
    )

    @abstractmethod
    def make_request(self, stub: pb2_grpc.SpawnerServiceStub, stream: str):
        """Convert the action to a gRPC request for the given stream."""
        pass


class HideAction(BaseModel):
    type: Literal["Hide"]
    reason: str = Field(
        default="",
        description="Reason for hiding the stream",
    )

    def make_request(self, stub: pb2_grpc.SpawnerServiceStub, stream: str):
        return stub.HideStream(
            pb2.HideStreamRequest(
                name=stream,
                reason_to_hide=self.reason,
            )
        )


class ShowAction(BaseModel):
    type: Literal["Show"]

    def make_request(self, stub: pb2_grpc.SpawnerServiceStub, stream: str):
        return stub.ShowStream(
            pb2.ShowStreamRequest(
                name=stream,
            )
        )


ArgusAction = Annotated[Union[HideAction, ShowAction], Field(discriminator="type")]


class InitialVisibilityCondition(BaseModel):
    hwobj_role: str = Field(
        description="Role of the hardware object to check for initial visibility",
    )
    attribute: str = Field(
        description="Attribute of the hardware object to check for initial visibility",
    )
    equals: Optional[str | int | bool] = Field(
        description="Value to compare against for initial visibility",
    )


class HiddenInitially(BaseModel):
    always: bool = Field(
        default=False, description="Set to true if always hidding initially"
    )
    when: InitialVisibilityCondition = Field(
        default=None,
        description="Condition for the stream to be hidden initially",
    )
    reason: str = Field(
        default="",
        description="Reason for hiding the stream initially",
    )


class ArgusStream(BaseModel):
    name: str = Field(
        description="Name of the stream",
    )
    create: bool = Field(
        default=False,
        description="Whether MXCuBE should create the stream or not",
    )
    uri: str = Field(
        default="test",
        description="URI to be passed to the streamer",
    )
    port: int = Field(
        default=7071,
        description="Port to be passed to the streamer",
    )
    main: bool = Field(
        default=False,
        description="Whether the stream is the main stream or not",
    )
    hidden_initially: HiddenInitially = Field(
        default=None,
        description="Whether the stream is hidden initially or not",
    )


class MultiView(BaseModel):
    name: str = Field(
        description="Name of the multiview",
    )
    streams: list[str] = Field(
        description="List of streams in the multiview",
    )


class TriggerEvent(BaseModel):
    hwobj_role: str = Field(
        description="Role of the hardware object triggering the event",
    )
    event: str = Field(
        description="Name of the event signal triggering the action",
    )


class TriggerCase(BaseModel):
    value: str | int | bool = Field(
        description="Value of the trigger case",
    )
    actions: list[ArgusAction] = Field(
        description="Actions to be taken when the trigger case is matched",
    )


class ArgusTrigger(BaseModel):
    name: str = Field(
        description="Name of the trigger",
    )
    streams: list[str] = Field(
        description="List of streams affected by the trigger",
    )
    on: list[TriggerEvent] = Field(
        description="List of signals triggering the event",
    )
    type: Literal["Argus", "MXCuBE"] = Field(
        default="Argus",
        description="Application type for the actions (Argus or MXCuBE)",
    )
    cases: list[TriggerCase] = Field(description="List of cases for the trigger")


class ArgusStreams(BaseModel):
    stream: list[ArgusStream]


class MultiViews(BaseModel):
    view: list[MultiView]


class ArgusTriggers(BaseModel):
    trigger: list[ArgusTrigger]


class ArgusConfig(BaseModel):
    grpc_url: str = Field(
        description="gRPC URL for the Argus server",
    )
    config_path: str = Field(
        description="path to argus configuration files",
    )
    exports: list[str] = Field(
        default_factory=list,
        description="List of exports to be configured",
    )
    streams: ArgusStreams = Field(
        description="List of streams to be configured",
    )
    multi_views: MultiViews = Field(
        default_factory=list,
        description="List of multiviews to be configured",
    )
    triggers: ArgusTriggers = Field(
        default_factory=list,
        description="List of triggers to be configured",
    )
