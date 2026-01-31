typescript
type Event = {
  id: string;
  name: string;
  description?: string;
  startDate: Date;
  endDate: Date;
  location: string;
  organizer: string;
  participants?: string[];
  status: 'planned' | 'canceled' | 'completed';
};