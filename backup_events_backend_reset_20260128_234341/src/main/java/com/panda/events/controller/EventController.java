package com.panda.events.controller;

import com.panda.events.dto.EventCreateRequest;
import com.panda.events.dto.EventResponse;
import com.panda.events.service.EventService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;

@CrossOrigin(origins = "http://localhost:4200")
@RestController
@RequestMapping("/api/events")
public class EventController {

    @Autowired
    private EventService eventService;

    @GetMapping
    public ResponseEntity<Page<EventResponse>> getEvents(@RequestParam(required = false) String q,
                                                         @RequestParam(required = false) OffsetDateTime from,
                                                         @RequestParam(required = false) OffsetDateTime to,
                                                         @RequestParam(required = false) String city,
                                                         @RequestParam(required = false) String category,
                                                         @RequestParam(defaultValue = "0") int page,
                                                         @RequestParam(defaultValue = "20") int size) {
        Page<EventResponse> events = eventService.findEvents(q, from, to, city, category, page, size);
        return ResponseEntity.ok(events);
    }

    @GetMapping("/{id}")
    public ResponseEntity<EventResponse> getEvent(@PathVariable Long id) {
        EventResponse event = eventService.getEvent(id);
        return ResponseEntity.ok(event);
    }

    @PostMapping
    public ResponseEntity<EventResponse> createEvent(@Valid @RequestBody EventCreateRequest request) {
        EventResponse createdEvent = eventService.createEvent(request);
        return ResponseEntity.status(201).body(createdEvent);
    }

    @PutMapping("/{id}")
    public ResponseEntity<EventResponse> updateEvent(@PathVariable Long id, @Valid @RequestBody EventCreateRequest request) {
        EventResponse updatedEvent = eventService.updateEvent(id, request);
        return ResponseEntity.ok(updatedEvent);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteEvent(@PathVariable Long id) {
        eventService.deleteEvent(id);
        return ResponseEntity.noContent().build();
    }
}
