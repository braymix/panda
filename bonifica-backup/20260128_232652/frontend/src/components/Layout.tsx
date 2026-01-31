Ecco un esempio di componente React per il layout che hai richiesto:

```jsx
import React from 'react';
import './Layout.css';

const Layout = ({ children }) => {
  return (
    <div className="layout">
      <header className="header">
        {/* Il tuo header o navbar va qui */}
        <nav>
          <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/about">About</a></li>
            <li><a href="/contact">Contact</a></li>
          </ul>
        </nav>
      </header>
      <div className="content-container">
        {children}
      </div>
    </div>
  );
};

export default Layout;
```

Ecco anche un esempio di stili CSS (`Layout.css`) per questo componente:

```css
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  background-color: #333;
  color: white;
  padding: 1rem;
  text-align: center;
}

.content-container {
  flex-grow: 1;
  padding: 2rem;
}
```

Questo layout include:

1. Un header con una navbar semplice
2. Un contenitore centrale (`content-container`) che può contenere qualsiasi elemento figlio passato al componente `Layout`
3. Lo stile di base per centrare il contenuto e assicurarsi che l'header abbia lo spazio necessario

Puoi modificare questo esempio per adattarlo alle tue esigenze specifiche, come cambiare lo stile dell'header o aggiungere ulteriori elementi.