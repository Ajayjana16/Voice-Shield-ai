import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught runtime error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 max-w-2xl mx-auto my-8 bg-red-50 border border-red-200 rounded-lg text-slate-800">
          <div className="flex items-center gap-2 text-red-700 font-bold mb-2">
            <AlertTriangle size={18} />
            <span>Display Recovered</span>
          </div>
          <p className="text-sm text-slate-700 mb-3">
            Unable to render component view:
          </p>
          <pre className="text-xs font-mono bg-white p-3 rounded border border-red-200 text-red-900 overflow-x-auto mb-4">
            {this.state.error?.message || "Unknown rendering error"}
          </pre>
          <button
            type="button"
            className="primary-cta-btn"
            onClick={this.handleReset}
          >
            <RefreshCw size={14} />
            <span>Retry</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
