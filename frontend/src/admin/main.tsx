import { createRoot } from 'react-dom/client';
import '../styles/base.css';
import '../styles/app.css';
import { AdminApp } from './App';
createRoot(document.getElementById('root')!).render(<AdminApp />);
