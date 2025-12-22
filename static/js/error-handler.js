/**
 * 错误处理和日志记录模块
 * 提供全局错误捕获、资源加载错误处理和用户友好的错误提示
 */

(function() {
  'use strict';

  // ==================== 错误处理配置 ====================
  const ERROR_CONFIG = {
    // 是否启用详细错误日志
    VERBOSE_LOGGING: false,
    // 错误报告端点
    ERROR_REPORT_URL: '/api/error-report/',
    // 最大错误缓存数量
    MAX_ERROR_CACHE: 50,
    // 错误重试次数
    MAX_RETRIES: 3,
    // 重试延迟（毫秒）
    RETRY_DELAY: 1000
  };

  // ==================== 错误管理器 ====================
  class ErrorManager {
    constructor() {
      this.errorCache = [];
      this.retryCount = new Map();
      this.init();
    }

    init() {
      this.setupGlobalErrorHandlers();
      this.setupResourceErrorHandlers();
      this.setupUnhandledRejectionHandler();
      this.setupNetworkErrorHandlers();
    }

    setupGlobalErrorHandlers() {
      // 捕获JavaScript运行时错误
      window.addEventListener('error', (event) => {
        this.handleJavaScriptError({
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          error: event.error,
          stack: event.error ? event.error.stack : null
        });
      });

      // 捕获未处理的Promise拒绝
      window.addEventListener('unhandledrejection', (event) => {
        this.handlePromiseRejection({
          reason: event.reason,
          promise: event.promise
        });
      });
    }

    setupResourceErrorHandlers() {
      // 全局资源加载错误处理函数
      window.resourceLoadError = (element) => {
        this.handleResourceError(element);
      };

      // 监听资源加载错误
      document.addEventListener('error', (event) => {
        if (event.target !== window) {
          this.handleResourceError(event.target);
        }
      }, true);
    }

    setupUnhandledRejectionHandler() {
      window.addEventListener('unhandledrejection', (event) => {
        console.error('未处理的Promise拒绝:', event.reason);
        
        // 阻止默认的控制台错误输出
        event.preventDefault();
        
        this.logError('promise_rejection', {
          reason: event.reason,
          stack: event.reason ? event.reason.stack : null
        });

        // 显示用户友好的错误消息
        this.showUserError('发生了一个意外错误，请刷新页面重试');
      });
    }

    setupNetworkErrorHandlers() {
      // 拦截fetch请求，添加错误处理
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        try {
          const response = await originalFetch(...args);
          
          if (!response.ok) {
            this.handleNetworkError({
              url: args[0],
              status: response.status,
              statusText: response.statusText
            });
          }
          
          return response;
        } catch (error) {
          this.handleNetworkError({
            url: args[0],
            error: error.message,
            type: 'fetch_error'
          });
          throw error;
        }
      };
    }

    handleJavaScriptError(errorInfo) {
      console.error('JavaScript错误:', errorInfo);
      
      this.logError('javascript_error', errorInfo);
      
      // 对于严重错误，显示用户提示
      if (this.isCriticalError(errorInfo)) {
        this.showUserError('页面功能可能受到影响，建议刷新页面');
      }
    }

    handlePromiseRejection(rejectionInfo) {
      console.error('Promise拒绝:', rejectionInfo);
      
      this.logError('promise_rejection', rejectionInfo);
      
      // 显示用户友好的错误消息
      this.showUserError('操作失败，请重试');
    }

    handleResourceError(element) {
      const resourceInfo = {
        tagName: element.tagName,
        src: element.src || element.href,
        type: element.type || 'unknown'
      };

      console.warn('资源加载失败:', resourceInfo);
      
      this.logError('resource_error', resourceInfo);
      
      // 尝试资源降级或重试
      this.attemptResourceFallback(element);
    }

    handleNetworkError(errorInfo) {
      console.error('网络错误:', errorInfo);
      
      this.logError('network_error', errorInfo);
      
      // 显示网络错误提示
      if (errorInfo.status >= 500) {
        this.showUserError('服务器暂时不可用，请稍后重试');
      } else if (errorInfo.status === 404) {
        this.showUserError('请求的资源不存在');
      } else if (errorInfo.status === 403) {
        this.showUserError('没有权限访问此资源');
      } else {
        this.showUserError('网络请求失败，请检查网络连接');
      }
    }

    attemptResourceFallback(element) {
      const src = element.src || element.href;
      const retryKey = src;
      const currentRetries = this.retryCount.get(retryKey) || 0;

      if (currentRetries >= ERROR_CONFIG.MAX_RETRIES) {
        console.error(`资源加载失败，已达到最大重试次数: ${src}`);
        this.handleResourceFallbackFailed(element);
        return;
      }

      // 增加重试计数
      this.retryCount.set(retryKey, currentRetries + 1);

      // 延迟重试
      setTimeout(() => {
        console.log(`重试加载资源 (${currentRetries + 1}/${ERROR_CONFIG.MAX_RETRIES}): ${src}`);
        
        if (element.tagName === 'LINK') {
          // CSS资源重试
          element.href = src + '?retry=' + (currentRetries + 1);
        } else if (element.tagName === 'SCRIPT') {
          // JavaScript资源重试
          element.src = src + '?retry=' + (currentRetries + 1);
        }
      }, ERROR_CONFIG.RETRY_DELAY * (currentRetries + 1));
    }

    handleResourceFallbackFailed(element) {
      const src = element.src || element.href;
      
      if (element.tagName === 'LINK' && element.rel === 'stylesheet') {
        // CSS资源完全失败，注入基础样式
        this.injectFallbackCSS();
        this.showUserError('部分样式文件加载失败，页面显示可能异常');
      } else if (element.tagName === 'SCRIPT') {
        // JavaScript资源完全失败
        this.showUserError('部分功能可能不可用，建议刷新页面');
      }
    }

    injectFallbackCSS() {
      // 注入最基本的CSS样式
      const fallbackCSS = `
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .btn { display: inline-block; padding: 8px 16px; margin: 4px; border: 1px solid #ccc; background: #f8f9fa; text-decoration: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background: #007bff; color: white; border-color: #007bff; }
        .form-control { width: 100%; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; }
        .alert { padding: 12px 16px; margin: 16px 0; border: 1px solid transparent; border-radius: 4px; }
        .alert-danger { color: #721c24; background: #f8d7da; border-color: #f5c6cb; }
      `;

      const style = document.createElement('style');
      style.textContent = fallbackCSS;
      document.head.appendChild(style);
    }

    isCriticalError(errorInfo) {
      // 判断是否为关键错误
      const criticalPatterns = [
        /Cannot read property/,
        /is not defined/,
        /is not a function/,
        /Maximum call stack/
      ];

      return criticalPatterns.some(pattern => 
        pattern.test(errorInfo.message)
      );
    }

    logError(type, details) {
      const errorEntry = {
        timestamp: new Date().toISOString(),
        type: type,
        details: details,
        userAgent: navigator.userAgent,
        url: window.location.href
      };

      // 添加到错误缓存
      this.errorCache.push(errorEntry);
      
      // 限制缓存大小
      if (this.errorCache.length > ERROR_CONFIG.MAX_ERROR_CACHE) {
        this.errorCache.shift();
      }

      // 详细日志记录
      if (ERROR_CONFIG.VERBOSE_LOGGING) {
        console.log('错误日志:', errorEntry);
      }

      // 发送错误报告（可选）
      this.sendErrorReport(errorEntry);
    }

    sendErrorReport(errorEntry) {
      // 发送错误报告到服务器（可选功能）
      if (ERROR_CONFIG.ERROR_REPORT_URL) {
        try {
          fetch(ERROR_CONFIG.ERROR_REPORT_URL, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(errorEntry)
          }).catch(() => {
            // 静默处理错误报告失败
          });
        } catch (e) {
          // 静默处理
        }
      }
    }

    showUserError(message, type = 'error') {
      // 显示用户友好的错误消息
      if (window.ui && window.ui.showToast) {
        window.ui.showToast(message, type, 5000);
      } else {
        // 降级到原生alert
        console.error(message);
        
        // 创建简单的错误提示
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: #f8d7da;
          color: #721c24;
          padding: 12px 16px;
          border: 1px solid #f5c6cb;
          border-radius: 4px;
          z-index: 10000;
          max-width: 300px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // 5秒后自动移除
        setTimeout(() => {
          if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
          }
        }, 5000);
      }
    }

    getErrorSummary() {
      // 获取错误摘要
      const summary = {
        totalErrors: this.errorCache.length,
        errorTypes: {},
        recentErrors: this.errorCache.slice(-5)
      };

      this.errorCache.forEach(error => {
        summary.errorTypes[error.type] = (summary.errorTypes[error.type] || 0) + 1;
      });

      return summary;
    }

    clearErrorCache() {
      this.errorCache = [];
      this.retryCount.clear();
    }
  }

  // ==================== 浏览器兼容性检查 ====================
  class CompatibilityChecker {
    constructor() {
      this.requiredFeatures = [
        'fetch',
        'Promise',
        'addEventListener',
        'querySelector'
      ];
    }

    checkCompatibility() {
      const missingFeatures = [];
      
      this.requiredFeatures.forEach(feature => {
        if (!this.isFeatureSupported(feature)) {
          missingFeatures.push(feature);
        }
      });

      if (missingFeatures.length > 0) {
        this.showCompatibilityWarning(missingFeatures);
        return false;
      }

      return true;
    }

    isFeatureSupported(feature) {
      switch (feature) {
        case 'fetch':
          return typeof fetch !== 'undefined';
        case 'Promise':
          return typeof Promise !== 'undefined';
        case 'addEventListener':
          return typeof window.addEventListener !== 'undefined';
        case 'querySelector':
          return typeof document.querySelector !== 'undefined';
        default:
          return true;
      }
    }

    showCompatibilityWarning(missingFeatures) {
      const message = `您的浏览器版本过旧，可能无法正常使用本系统。缺少功能: ${missingFeatures.join(', ')}。建议升级到最新版本的Chrome、Firefox或Edge浏览器。`;
      
      // 创建兼容性警告
      const warningDiv = document.createElement('div');
      warningDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: #fff3cd;
        color: #856404;
        padding: 16px;
        border-bottom: 1px solid #ffeaa7;
        z-index: 10001;
        text-align: center;
        font-size: 14px;
      `;
      warningDiv.innerHTML = `
        <strong>浏览器兼容性警告:</strong> ${message}
        <button onclick="this.parentNode.style.display='none'" style="margin-left: 10px; padding: 4px 8px; border: 1px solid #856404; background: transparent; cursor: pointer;">关闭</button>
      `;
      
      document.body.insertBefore(warningDiv, document.body.firstChild);
    }
  }

  // ==================== 性能监控 ====================
  class PerformanceMonitor {
    constructor() {
      this.metrics = {};
      this.init();
    }

    init() {
      // 监控页面加载性能
      window.addEventListener('load', () => {
        this.collectLoadMetrics();
      });

      // 监控资源加载性能
      this.monitorResourceTiming();
    }

    collectLoadMetrics() {
      if (window.performance && window.performance.timing) {
        const timing = window.performance.timing;
        
        this.metrics = {
          // 页面加载时间
          pageLoadTime: timing.loadEventEnd - timing.navigationStart,
          // DOM解析时间
          domParseTime: timing.domContentLoadedEventEnd - timing.domLoading,
          // 资源加载时间
          resourceLoadTime: timing.loadEventEnd - timing.domContentLoadedEventEnd,
          // 首次内容绘制时间
          firstContentfulPaint: this.getFirstContentfulPaint(),
          // 最大内容绘制时间
          largestContentfulPaint: this.getLargestContentfulPaint()
        };

        // 记录性能指标
        console.log('页面性能指标:', this.metrics);
        
        // 检查性能问题
        this.checkPerformanceIssues();
      }
    }

    getFirstContentfulPaint() {
      if (window.performance && window.performance.getEntriesByType) {
        const paintEntries = window.performance.getEntriesByType('paint');
        const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
        return fcpEntry ? fcpEntry.startTime : null;
      }
      return null;
    }

    getLargestContentfulPaint() {
      return new Promise((resolve) => {
        if (window.PerformanceObserver) {
          const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            resolve(lastEntry ? lastEntry.startTime : null);
          });
          observer.observe({ entryTypes: ['largest-contentful-paint'] });
          
          // 10秒后超时
          setTimeout(() => resolve(null), 10000);
        } else {
          resolve(null);
        }
      });
    }

    monitorResourceTiming() {
      if (window.PerformanceObserver) {
        const observer = new PerformanceObserver((list) => {
          list.getEntries().forEach(entry => {
            if (entry.duration > 3000) { // 超过3秒的资源
              console.warn('慢速资源加载:', {
                name: entry.name,
                duration: entry.duration,
                size: entry.transferSize
              });
            }
          });
        });
        observer.observe({ entryTypes: ['resource'] });
      }
    }

    checkPerformanceIssues() {
      const issues = [];
      
      if (this.metrics.pageLoadTime > 5000) {
        issues.push('页面加载时间过长');
      }
      
      if (this.metrics.domParseTime > 2000) {
        issues.push('DOM解析时间过长');
      }
      
      if (this.metrics.firstContentfulPaint > 3000) {
        issues.push('首次内容绘制时间过长');
      }

      if (issues.length > 0) {
        console.warn('性能问题:', issues);
        
        if (window.errorManager) {
          window.errorManager.logError('performance_issue', {
            issues: issues,
            metrics: this.metrics
          });
        }
      }
    }
  }

  // ==================== 初始化 ====================
  
  // 创建全局实例
  window.errorManager = new ErrorManager();
  window.compatibilityChecker = new CompatibilityChecker();
  window.performanceMonitor = new PerformanceMonitor();

  // 检查浏览器兼容性
  document.addEventListener('DOMContentLoaded', () => {
    window.compatibilityChecker.checkCompatibility();
  });

  console.log('错误处理和监控系统已初始化');

})();