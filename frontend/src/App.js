import "@/App.css";
import { useEffect } from "react";

function App() {
  useEffect(() => {
    // Redirect to the static landing page immediately
    window.location.replace("/landing.html");
  }, []);
  return (
    <div className="App" data-testid="si-ispo-app" style={{background:"#F5F8F4",minHeight:"100vh"}} />
  );
}

export default App;
