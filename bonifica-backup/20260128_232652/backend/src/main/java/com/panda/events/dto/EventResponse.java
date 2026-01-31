java
import java.time.OffsetDateTime;
import java.util.UUID;

public class EventResponse {
    private UUID id;
    private String name;
    private String description;
    private OffsetDateTime startAt;
    private OffsetDateTime endAt;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    private EventResponse(UUID id, String name, String description, OffsetDateTime startAt, OffsetDateTime endAt, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.startAt = startAt;
        this.endAt = endAt;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public OffsetDateTime getStartAt() {
        return startAt;
    }

    public OffsetDateTime getEndAt() {
        return endAt;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public static EventResponse fromEntity(Event event) {
        return new EventResponse(
            event.getId(),
            event.getName(),
            event.getDescription(),
            event.getStartAt(),
            event.getEndAt(),
            event.getCreatedAt(),
            event.getUpdatedAt()
        );
    }
}