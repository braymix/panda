import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;


@Service
public class EventService {

    @Autowired
    private EventRepository eventRepository;

    public Page<Event> search(String q, OffsetDateTime from, OffsetDateTime to, String city, String category, Pageable pageable) {
        return eventRepository.findAll((Specification<Event>) (root, query, criteriaBuilder) -> {
            List<Predicate> predicates = new ArrayList<>();

            if (q != null) {
                predicates.add(criteriaBuilder.or(
                    criteriaBuilder.like(criteriaBuilder.lower(root.get("title")), "%" + q.toLowerCase() + "%"),
                    criteriaBuilder.like(criteriaBuilder.lower(root.get("description")), "%" + q.toLowerCase() + "%")
                ));
            }

            if (from != null) {
                predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("startAt"), from));
            }

            if (to != null) {
                predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("startAt"), to));
            }

            if (city != null) {
                predicates.add(criteriaBuilder.equal(criteriaBuilder.lower(root.get("city")), city.toLowerCase()));
            }

            if (category != null) {
                predicates.add(criteriaBuilder.equal(criteriaBuilder.lower(root.get("category")), category.toLowerCase()));
            }

            query.where(predicates.toArray(new Predicate[0]));
            return query;
        }, pageable);
    }

    public Event get(UUID id) throws NotFoundException {
        Optional<Event> event = eventRepository.findById(id);
        if (event.isPresent()) {
            return event.get();
        } else {
            throw new NotFoundException("Event not found with id: " + id);
        }
    }

    public Event create(EventCreateRequest req) {
        Event event = new Event(req.getTitle(), req.getDescription(), req.getStartAt(), req.getEndAt(), req.getLocation(), req.getCity(), req.getCategory());
        return eventRepository.save(event);
    }

    public Event update(UUID id, EventCreateRequest req) throws NotFoundException {
        Optional<Event> optionalEvent = eventRepository.findById(id);
        if (optionalEvent.isPresent()) {
            Event event = optionalEvent.get();
            event.setTitle(req.getTitle());
            event.setDescription(req.getDescription());
            event.setStartAt(req.getStartAt());
            event.setEndAt(req.getEndAt());
            event.setLocation(req.getLocation());
            event.setCity(req.getCity());
            event.setCategory(req.getCategory());
            return eventRepository.save(event);
        } else {
            throw new NotFoundException("Event not found with id: " + id);
        }
    }

    public void delete(UUID id) throws NotFoundException {
        if (eventRepository.existsById(id)) {
            eventRepository.deleteById(id);
        } else {
            throw new NotFoundException("Event not found with id: " + id);
        }
    }
}
