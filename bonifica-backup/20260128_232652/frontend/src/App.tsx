tsx
import React from 'react';
import { BrowserRouter as Router, Route, Switch, Link } from 'react-router-dom';

const EventsListPage = () => <h1>Events List Page</h1>;
const EventDetailPage = ({ match }: { match: any }) => (
  <h1>Event Detail Page for {match.params.id}</h1>
);
const EventCreatePage = () => <h1>Create Event Page</h1>;

const App = () => (
  <Router>
    <nav>
      <Link to="/">Home</Link> | 
      <Link to="/create">Create Event</Link>
    </nav>

    <Switch>
      <Route exact path="/" component={EventsListPage} />
      <Route path="/events/:id" component={EventDetailPage} />
      <Route path="/create" component={EventCreatePage} />
    </Switch>
  </Router>
);

export default App;