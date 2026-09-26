from pydantic import BaseModel, ConfigDict, Field


class HourlyBucketDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hour: str
    timestamp: int | float
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    errors: int = 0


class OverviewDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    error_rate_pct: float
    active_keys: int
    blocked_ips_count: int
    timeseries_24h: list[HourlyBucketDTO] = []


class HealthDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_loaded: bool
    model_id: str
    device: str
    memory_rss_mb: float
    uptime_seconds: float
    database_size_bytes: int


class KeyCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    rate_limit: int | None = Field(None, gt=0)


class KeyUpdateDTO(BaseModel):
    is_active: bool | None = None
    rate_limit: int | None = Field(None, gt=0)


class KeyResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    name: str
    rate_limit: int | None = None
    is_active: bool
    created_at: str | None = None
    last_used_at: str | None = None


class KeyCreateResponseDTO(KeyResponseDTO):
    raw_key: str


class LogItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: float
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    ip_address: str
    api_key_id: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class LogsResponseDTO(BaseModel):
    items: list[LogItemDTO]
    total: int
    page: int
    limit: int
    pages: int


class KeyActivityResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    error_rate_pct: float
    timeseries_24h: list[HourlyBucketDTO]
    recent_logs: list[LogItemDTO]


class SettingsUpdateDTO(BaseModel):
    rate_limit_requests: int = Field(..., gt=0)
    rate_limit_window_seconds: int = Field(..., gt=0)


class BlocklistCreateDTO(BaseModel):
    ip_address: str = Field(..., min_length=1, max_length=64)
    reason: str = Field("", max_length=256)


class BlocklistItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    reason: str
    created_at: str | None = None


class KeyActionResponseDTO(BaseModel):
    success: bool = True
    key_id: int


class DeleteResponseDTO(BaseModel):
    success: bool = True


class BlocklistActionResponseDTO(BaseModel):
    success: bool = True
    ip_address: str

