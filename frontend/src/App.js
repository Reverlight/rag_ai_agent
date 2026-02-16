import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader, Send, Book } from 'lucide-react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle');
  const [uploadMessage, setUploadMessage] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [queryStatus, setQueryStatus] = useState('idle');
  const [events, setEvents] = useState([]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setUploadStatus('idle');
      setUploadMessage('');
    } else {
      alert('Please select a valid PDF file');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploadStatus('uploading');
    setUploadMessage('Uploading and processing PDF...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setUploadStatus('success');
      setUploadMessage(`PDF processed successfully! Processing started for ${file.name}`);
      addEvent({ type: 'success', message: `Uploaded: ${file.name}`, time: new Date() });
    } catch (error) {
      setUploadStatus('error');
      setUploadMessage(`Error: ${error.message}`);
      addEvent({ type: 'error', message: error.message, time: new Date() });
    }
  };

  const handleQuery = async () => {
    if (!question.trim()) return;

    setQueryStatus('loading');
    setAnswer(null);

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Query failed: ${response.statusText}`);
      }

      const data = await response.json();
      setAnswer(data);
      setQueryStatus('success');
      addEvent({ type: 'query', message: `Query: "${question.substring(0, 50)}..."`, time: new Date() });
    } catch (error) {
      setQueryStatus('error');
      setAnswer({ error: error.message });
      addEvent({ type: 'error', message: error.message, time: new Date() });
    }
  };

  const addEvent = (event) => {
    setEvents(prev => [event, ...prev].slice(0, 10));
  };

  return (
    <div className="app">
      <div className="container">
        <div className="header">
          <h1>
            <Book size={48} />
            RAG PDF Assistant
          </h1>
          <p>Upload PDFs and query their content with AI</p>
        </div>

        <div className="grid">
          {/* Upload Section */}
          <div className="card">
            <h2>
              <Upload size={24} />
              Upload PDF
            </h2>

            <div className="upload-area">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="file-label">
                <FileText size={48} />
                <span>{file ? file.name : 'Click to select PDF file'}</span>
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || uploadStatus === 'uploading'}
              className="btn btn-primary"
            >
              {uploadStatus === 'uploading' ? (
                <>
                  <Loader size={20} className="spin" />
                  Processing...
                </>
              ) : (
                'Upload & Process'
              )}
            </button>

            {uploadMessage && (
              <div className={`message message-${uploadStatus}`}>
                {uploadStatus === 'success' && <CheckCircle size={20} />}
                {uploadStatus === 'error' && <XCircle size={20} />}
                <p>{uploadMessage}</p>
              </div>
            )}
          </div>

          {/* Query Section */}
          <div className="card">
            <h2>
              <Send size={24} />
              Ask Questions
            </h2>

            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your uploaded PDFs..."
              className="textarea"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleQuery();
                }
              }}
            />
            <p className="hint">Press Ctrl+Enter to submit</p>

            <button
              onClick={handleQuery}
              disabled={!question.trim() || queryStatus === 'loading'}
              className="btn btn-secondary"
            >
              {queryStatus === 'loading' ? (
                <>
                  <Loader size={20} className="spin" />
                  Searching...
                </>
              ) : (
                'Get Answer'
              )}
            </button>

            {answer && (
              <div className="answer-box">
                {answer.error ? (
                  <div className="error-result">
                    <XCircle size={20} />
                    <p>{answer.error}</p>
                  </div>
                ) : (
                  <>
                    <div className="answer-section">
                      <h3>Answer</h3>
                      <p>{answer.answer}</p>
                    </div>
                    {answer.sources && answer.sources.length > 0 && (
                      <div className="sources-section">
                        <h3>Sources</h3>
                        <div className="sources">
                          {answer.sources.map((source, i) => (
                            <span key={i} className="source-tag">
                              {source}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {answer.num_contexts && (
                      <p className="context-info">
                        Used {answer.num_contexts} context{answer.num_contexts !== 1 ? 's' : ''}
                      </p>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Activity Log */}
        {events.length > 0 && (
          <div className="card activity-log">
            <h2>Recent Activity</h2>
            <div className="events">
              {events.map((event, i) => (
                <div key={i} className="event-item">
                  {event.type === 'success' && <CheckCircle size={16} className="icon-success" />}
                  {event.type === 'error' && <XCircle size={16} className="icon-error" />}
                  {event.type === 'query' && <Send size={16} className="icon-query" />}
                  <span className="event-message">{event.message}</span>
                  <span className="event-time">
                    {event.time.toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;