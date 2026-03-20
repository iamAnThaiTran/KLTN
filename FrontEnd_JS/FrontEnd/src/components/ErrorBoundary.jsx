import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('💥 Component Error:', error);
    console.error('ℹ️ Error Info:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          width: '100vw',
          background: '#fff',
          flexDirection: 'column',
          gap: 20,
          padding: 20,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 48 }}>⚠️</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#1e293b' }}>
            Đã xảy ra lỗi
          </div>
          <div style={{
            background: '#f1f5f9',
            padding: 16,
            borderRadius: 8,
            maxWidth: 600,
            fontSize: 12,
            fontFamily: 'monospace',
            color: '#e11d48',
            overflow: 'auto',
            maxHeight: 200,
          }}>
            {this.state.error?.toString()}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px',
              background: '#6366f1',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 600,
              marginTop: 12,
            }}
          >
            Reload trang
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
