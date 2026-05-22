import "@/App.css";

function App() {
  return (
    <div className="App" data-testid="si-ispo-app">
      <iframe
        title="SI-ISPO Sistem Informasi ISPO"
        src="/si-ispo.html"
        data-testid="si-ispo-frame"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          border: "none",
          margin: 0,
          padding: 0,
        }}
      />
    </div>
  );
}

export default App;
