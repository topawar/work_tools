/**
 * 性能监控和优化脚本
 * 提供页面性能监控、资源懒加载等功能
 */

(function() {
  'use strict';

  // ==================== 性能监控配置 ====================
  const PERF_CONFIG = {
    // 性能阈值
    SLOW_LOAD_THRESHOLD: 3000,      // 慢加载阈值（毫秒）
    LARGE_RESOURCE_THRESHOLD: 1024 * 1024, // 大资源阈值（1MB）
    
    // 监控开关
    ENABLE_RESOURCE_TIMING: true,
    ENABLE_NAVIGATION_TIMING: true,
    ENABLE_PAINT_TIMING: true,
    
    // 报告配置
    REPORT_INTERVAL: 30000,         // 报告间隔（毫秒）
    MAX_REPORTS: 10                 // 最大报告数量
  };

  // ==================== 性能监控器 ====================
  class PerformanceMonitor {
    constructor() {
      this.metrics = {};
      this.reports = [];
      this.observers = [];
      this.init();
    }

    init() {
      // 等待页面加载完成
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.startMonitoring());
      } else {
        this.startMonitoring();
      }
    }

    startMonitoring() {
      this.monitorNavigationTiming();
      this.monitorResourceTiming();
      this.monitorPaintTiming();
      this.monitorLargestContentfulPaint();
      this.monitorCumulativeLayoutShift();
      this.monitorFirstInputDelay();
      
      // 定期生成报告
      setInterval(() => this.generateReport(), PERF_CONFIG.REPORT_INTERVAL);
    }

    monitorNavigationTiming() {
      if (!PERF_CONFIG.ENABLE_NAVIGATION_TIMING || !window.performance || !window.performance.timing) {
        return;
      }

      window.addEventListener('load', () => {
        const timing = window.performance.timing;
        
        this.metrics.navigation = {
          // DNS查询时间
          dnsLookup: timing.domainLookupEnd - timing.domainLookupStart,
          // TCP连接时间
          tcpConnect: timing.connectEnd - timing.connectStart,
          // 请求响应时间
          request: timing.responseEnd - timing.requestStart,
          // DOM解析时间
          domParse: timing.domContentLoadedEventEnd - timing.domLoading,
          // 资源加载时间
          resourceLoad: timing.loadEventEnd - timing.domContentLoadedEventEnd,
          // 总页面加载时间
          totalLoad: timing.loadEventEnd - timing.navigationStart
        };

        // 检查慢加载
        if (this.metrics.navigation.totalLoad > PERF_CONFIG.SLOW_LOAD_THRESHOLD) {
          this.reportSlowLoad(this.metrics.navigation.totalLoad);
        }

        console.log('导航时间指标:', this.metrics.navigation);
      });
    }

    monitorResourceTiming() {
      if (!PERF_CONFIG.ENABLE_RESOURCE_TIMING || !window.PerformanceObserver) {
        return;
      }

      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach(entry => {
          // 监控大资源
          if (entry.transferSize > PERF_CONFIG.LARGE_RESOURCE_THRESHOLD) {
            this.reportLargeResource(entry);
          }

          // 监控慢资源
          if (entry.duration > PERF_CONFIG.SLOW_LOAD_THRESHOLD) {
            this.reportSlowResource(entry);
          }

          // 监控失败的资源
          if (entry.responseEnd === 0) {
            this.reportFailedResource(entry);
          }
        });
      });

      try {
        observer.observe({ entryTypes: ['resource'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('资源时间监控不支持:', e);
      }
    }

    monitorPaintTiming() {
      if (!PERF_CONFIG.ENABLE_PAINT_TIMING || !window.PerformanceObserver) {
        return;
      }

      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach(entry => {
          this.metrics[entry.name] = entry.startTime;
        });

        // 检查首次内容绘制时间
        if (this.metrics['first-contentful-paint'] > PERF_CONFIG.SLOW_LOAD_THRESHOLD) {
          this.reportSlowPaint('first-contentful-paint', this.metrics['first-contentful-paint']);
        }

        console.log('绘制时间指标:', {
          'first-paint': this.metrics['first-paint'],
          'first-contentful-paint': this.metrics['first-contentful-paint']
        });
      });

      try {
        observer.observe({ entryTypes: ['paint'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('绘制时间监控不支持:', e);
      }
    }

    monitorLargestContentfulPaint() {
      if (!window.PerformanceObserver) return;

      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        
        this.metrics.largestContentfulPaint = lastEntry.startTime;
        
        // LCP应该在2.5秒内
        if (lastEntry.startTime > 2500) {
          this.reportSlowPaint('largest-contentful-paint', lastEntry.startTime);
        }
      });

      try {
        observer.observe({ entryTypes: ['largest-contentful-paint'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('LCP监控不支持:', e);
      }
    }

    monitorCumulativeLayoutShift() {
      if (!window.PerformanceObserver) return;

      let clsValue = 0;
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        }
        
        this.metrics.cumulativeLayoutShift = clsValue;
        
        // CLS应该小于0.1
        if (clsValue > 0.1) {
          this.reportHighCLS(clsValue);
        }
      });

      try {
        observer.observe({ entryTypes: ['layout-shift'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('CLS监控不支持:', e);
      }
    }

    monitorFirstInputDelay() {
      if (!window.PerformanceObserver) return;

      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.metrics.firstInputDelay = entry.processingStart - entry.startTime;
          
          // FID应该小于100ms
          if (this.metrics.firstInputDelay > 100) {
            this.reportHighFID(this.metrics.firstInputDelay);
          }
          
          // 只需要第一次输入延迟
          observer.disconnect();
        }
      });

      try {
        observer.observe({ entryTypes: ['first-input'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('FID监控不支持:', e);
      }
    }

    reportSlowLoad(duration) {
      console.warn(`页面加载缓慢: ${duration}ms`);
      this.addReport('slow_load', { duration });
    }

    reportLargeResource(entry) {
      console.warn(`大资源文件: ${entry.name} (${(entry.transferSize / 1024 / 1024).toFixed(2)}MB)`);
      this.addReport('large_resource', {
        name: entry.name,
        size: entry.transferSize,
        duration: entry.duration
      });
    }

    reportSlowResource(entry) {
      console.warn(`资源加载缓慢: ${entry.name} (${entry.duration}ms)`);
      this.addReport('slow_resource', {
        name: entry.name,
        duration: entry.duration
      });
    }

    reportFailedResource(entry) {
      console.error(`资源加载失败: ${entry.name}`);
      this.addReport('failed_resource', {
        name: entry.name
      });
    }

    reportSlowPaint(type, duration) {
      console.warn(`${type}缓慢: ${duration}ms`);
      this.addReport('slow_paint', { type, duration });
    }

    reportHighCLS(value) {
      console.warn(`累积布局偏移过高: ${value}`);
      this.addReport('high_cls', { value });
    }

    reportHighFID(delay) {
      console.warn(`首次输入延迟过高: ${delay}ms`);
      this.addReport('high_fid', { delay });
    }

    addReport(type, data) {
      const report = {
        type,
        data,
        timestamp: Date.now(),
        url: window.location.href
      };

      this.reports.push(report);

      // 限制报告数量
      if (this.reports.length > PERF_CONFIG.MAX_REPORTS) {
        this.reports.shift();
      }

      // 发送到错误管理器
      if (window.errorManager) {
        window.errorManager.logError('performance_issue', report);
      }
    }

    generateReport() {
      const report = {
        timestamp: Date.now(),
        url: window.location.href,
        metrics: this.metrics,
        issues: this.reports.slice(-5), // 最近5个问题
        userAgent: navigator.userAgent,
        connection: this.getConnectionInfo()
      };

      console.log('性能报告:', report);
      return report;
    }

    getConnectionInfo() {
      if (navigator.connection) {
        return {
          effectiveType: navigator.connection.effectiveType,
          downlink: navigator.connection.downlink,
          rtt: navigator.connection.rtt
        };
      }
      return null;
    }

    cleanup() {
      // 清理观察器
      this.observers.forEach(observer => {
        try {
          observer.disconnect();
        } catch (e) {
          // 忽略清理错误
        }
      });
      this.observers = [];
    }
  }

  // ==================== 资源懒加载 ====================
  class LazyLoader {
    constructor() {
      this.imageObserver = null;
      this.init();
    }

    init() {
      this.setupImageLazyLoading();
      this.setupScriptLazyLoading();
    }

    setupImageLazyLoading() {
      if (!window.IntersectionObserver) {
        // 降级：立即加载所有图片
        this.loadAllImages();
        return;
      }

      this.imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            this.loadImage(entry.target);
            this.imageObserver.unobserve(entry.target);
          }
        });
      }, {
        rootMargin: '50px 0px' // 提前50px开始加载
      });

      // 观察所有懒加载图片
      document.querySelectorAll('img[data-src]').forEach(img => {
        this.imageObserver.observe(img);
      });
    }

    loadImage(img) {
      const src = img.getAttribute('data-src');
      if (src) {
        img.src = src;
        img.removeAttribute('data-src');
        img.classList.add('loaded');
      }
    }

    loadAllImages() {
      document.querySelectorAll('img[data-src]').forEach(img => {
        this.loadImage(img);
      });
    }

    setupScriptLazyLoading() {
      // 懒加载非关键JavaScript
      document.querySelectorAll('script[data-src]').forEach(script => {
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              this.loadScript(script);
              observer.unobserve(script);
            }
          });
        });

        observer.observe(script);
      });
    }

    loadScript(script) {
      const src = script.getAttribute('data-src');
      if (src) {
        script.src = src;
        script.removeAttribute('data-src');
      }
    }
  }

  // ==================== 初始化 ====================
  
  // 创建全局实例
  window.performanceMonitor = new PerformanceMonitor();
  window.lazyLoader = new LazyLoader();

  // 页面卸载时清理
  window.addEventListener('beforeunload', () => {
    if (window.performanceMonitor) {
      window.performanceMonitor.cleanup();
    }
  });

  console.log('性能监控和优化系统已初始化');

})();