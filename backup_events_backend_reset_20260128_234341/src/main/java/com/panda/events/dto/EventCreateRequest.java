package com.panda.events.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

public class EventCreateRequest {

    @NotBlank(message = "Title cannot be blank")
    @Size(max = 200, message = "Title must not exceed 200 characters")
    private String title;

    @Size(max = 120, message = "City must not exceed 120 characters")
    private String city;

    @Size(max = 200, message = "Venue must not exceed 200 characters")
    private String venue;

    @NotBlank(message = "Category cannot be blank")
    @Size(max = 80, message = "Category must not exceed 80 characters")
    private String category;

    @NotNull(message = "Start time cannot be null")
    private OffsetDateTime startAt;

    @Size(max = 400, message = "URL must not exceed 400 characters")
    private String url;

    public EventCreateRequest() {
    }

    // Getters and Setters

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getVenue() {
        return venue;
    }

    public void setVenue(String venue) {
        this.venue = venue;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public OffsetDateTime getStartAt() {
        return startAt;
    }

    public void setStartAt(OffsetDateTime startAt) {
        this.startAt = startAt;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }
}
