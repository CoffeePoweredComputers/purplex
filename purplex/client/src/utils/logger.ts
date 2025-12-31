/**
 * Centralized logging utility for Purplex frontend
 *
 * This utility provides structured logging that can be easily controlled
 * based on environment and configured for different log levels.
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 4
}

interface LogEntry {
  level: LogLevel;
  message: string;
  data?: unknown;
  timestamp: string;
  component?: string;
}

class Logger {
  private currentLevel: LogLevel;
  private isDevelopment: boolean;
  private logBuffer: LogEntry[] = [];
  private maxBufferSize = 100;

  constructor() {
    this.isDevelopment = import.meta.env.MODE === 'development' || import.meta.env.DEV;

    // Set log level based on environment
    if (this.isDevelopment) {
      this.currentLevel = LogLevel.DEBUG;
    } else {
      // In production, only log warnings and errors
      this.currentLevel = LogLevel.WARN;
    }
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.currentLevel;
  }

  private formatMessage(level: LogLevel, message: string, component?: string): string {
    const timestamp = new Date().toISOString();
    const levelName = LogLevel[level];
    const componentPrefix = component ? `[${component}] ` : '';
    return `[${timestamp}] ${levelName}: ${componentPrefix}${message}`;
  }

  private addToBuffer(entry: LogEntry): void {
    this.logBuffer.push(entry);
    if (this.logBuffer.length > this.maxBufferSize) {
      this.logBuffer.shift(); // Remove oldest entry
    }
  }

  private log(level: LogLevel, message: string, data?: unknown, component?: string): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      data,
      timestamp: new Date().toISOString(),
      component
    };

    this.addToBuffer(entry);

    const formattedMessage = this.formatMessage(level, message, component);

    // Only output to console in development or for errors/warnings
    if (this.isDevelopment || level >= LogLevel.WARN) {
      switch (level) {
        case LogLevel.DEBUG:
          console.debug(formattedMessage, data || '');
          break;
        case LogLevel.INFO:
          console.info(formattedMessage, data || '');
          break;
        case LogLevel.WARN:
          console.warn(formattedMessage, data || '');
          break;
        case LogLevel.ERROR:
          console.error(formattedMessage, data || '');
          break;
      }
    }

    // In production, you could send errors to a logging service
    if (!this.isDevelopment && level === LogLevel.ERROR) {
      this.sendToLoggingService(entry);
    }
  }

  private sendToLoggingService(_entry: LogEntry): void {
    // Placeholder for production logging service integration
    // Could send to Sentry, LogRocket, or custom endpoint
    try {
      // Example: Send to backend logging endpoint
      // fetch('/api/logs/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(entry)
      // }).catch(() => {}); // Silently fail if logging service is down
    } catch {
      // Silently fail - don't let logging break the app
    }
  }

  // Public API
  debug(message: string, data?: unknown, component?: string): void {
    this.log(LogLevel.DEBUG, message, data, component);
  }

  info(message: string, data?: unknown, component?: string): void {
    this.log(LogLevel.INFO, message, data, component);
  }

  warn(message: string, data?: unknown, component?: string): void {
    this.log(LogLevel.WARN, message, data, component);
  }

  error(message: string, data?: unknown, component?: string): void {
    this.log(LogLevel.ERROR, message, data, component);
  }

  // Utility methods
  getLogBuffer(): LogEntry[] {
    return [...this.logBuffer];
  }

  clearBuffer(): void {
    this.logBuffer = [];
  }

  setLogLevel(level: LogLevel): void {
    this.currentLevel = level;
  }

  // Component-specific loggers
  createComponentLogger(componentName: string) {
    return {
      debug: (message: string, data?: unknown) => this.debug(message, data, componentName),
      info: (message: string, data?: unknown) => this.info(message, data, componentName),
      warn: (message: string, data?: unknown) => this.warn(message, data, componentName),
      error: (message: string, data?: unknown) => this.error(message, data, componentName),
    };
  }
}

// Export singleton instance
export const logger = new Logger();

// Export convenience functions for common usage
export const log = {
  debug: logger.debug.bind(logger),
  info: logger.info.bind(logger),
  warn: logger.warn.bind(logger),
  error: logger.error.bind(logger),
  createComponentLogger: logger.createComponentLogger.bind(logger)
};
