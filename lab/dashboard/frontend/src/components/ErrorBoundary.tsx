import { Component, ReactNode } from "react";

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; message: string; }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-400 text-xs">
          <p className="font-semibold mb-1">渲染出错</p>
          <p className="text-red-500/70 font-mono">{this.state.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
