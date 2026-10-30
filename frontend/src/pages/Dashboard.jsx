import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

function Dashboard() {
  const navigate = useNavigate();

  const [url, setUrl] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!token) {
      navigate("/login");
      return;
    }

    loadUrls();
  }, []);

  async function loadUrls() {
    try {
      const response = await api.get("/urls", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setItems(response.data);
    } catch {
      localStorage.removeItem("token");
      navigate("/login");
    }
  }

  async function addUrl(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.post(
        "/urls",
        { url },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setItems((oldItems) => [response.data, ...oldItems]);
      setUrl("");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create preview");
    } finally {
      setLoading(false);
    }
  }

  async function deleteUrl(id) {
    try {
      await api.delete(`/urls/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setItems((oldItems) => oldItems.filter((item) => item.id !== id));
    } catch {
      setError("Could not delete URL");
    }
  }

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="dashboard">
      <header>
        <h1>URL Preview</h1>
        <button className="logout" onClick={logout}>Logout</button>
      </header>

      <main>
        <div className="card wide">
          <h2>Add a website</h2>

          <form onSubmit={addUrl} className="url-form">
            <input
              type="text"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Preview"}
            </button>
          </form>

          {error && <div className="error">{error}</div>}
        </div>

        <h2 className="saved-title">Saved websites</h2>

        {items.length === 0 ? (
          <div className="empty">No saved websites yet.</div>
        ) : (
          <div className="grid">
            {items.map((item) => (
              <div className="preview-card" key={item.id}>
                <img
                  src={`http://localhost:8000${item.preview_url}`}
                  alt="Website preview"
                />

                <div className="preview-content">
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.url}
                  </a>

                  <button
                    className="delete"
                    onClick={() => deleteUrl(item.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default Dashboard;
