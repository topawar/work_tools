/**
 * Work Tools UI 增强脚本
 * 提供现代化的交互体验
 */

(function() {
  'use strict';

  // ==================== 全局配置 ====================
  const CONFIG = {
    ANIMATION_DURATION: 300,
    DEBOUNCE_DELAY: 300,
    TOAST_DURATION: 4000,
    LOADING_MIN_DURATION: 500
  };

  // ==================== 工具函数 ====================
  
  /**
   * 防抖函数
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * 节流函数
   */
  function throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  /**
   * 创建DOM元素
   */
  function createElement(tag, className, innerHTML) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (innerHTML) element.innerHTML = innerHTML;
    return element;
  }

  // ==================== 加载状态管理 ====================
  
  class LoadingManager {
    constructor() {
      this.overlay = null;
      this.isLoading = false;
      this.startTime = null;
    }

    show(message = '处理中...') {
      if (this.isLoading) return;
      
      this.isLoading = true;
      this.startTime = Date.now();
      
      this.overlay = createElement('div', 'loading-overlay');
      this.overlay.innerHTML = `
        <div class="loading-content">
          <div class="loading-spinner"></div>
          <div class="loading-text">${message}</div>
        </div>
      `;
      
      document.body.appendChild(this.overlay);
      
      // 添加淡入动画
      requestAnimationFrame(() => {
        this.overlay.style.opacity = '1';
      });
    }

    hide() {
      if (!this.isLoading || !this.overlay) return;
      
      const elapsed = Date.now() - this.startTime;
      const minDelay = Math.max(0, CONFIG.LOADING_MIN_DURATION - elapsed);
      
      setTimeout(() => {
        if (this.overlay) {
          this.overlay.style.opacity = '0';
          setTimeout(() => {
            if (this.overlay && this.overlay.parentNode) {
              this.overlay.parentNode.removeChild(this.overlay);
            }
            this.overlay = null;
            this.isLoading = false;
          }, CONFIG.ANIMATION_DURATION);
        }
      }, minDelay);
    }
  }

  // ==================== 消息提示系统 ====================
  
  class ToastManager {
    constructor() {
      this.container = null;
      this.toasts = [];
      this.init();
    }

    init() {
      this.container = createElement('div', 'toast-container');
      this.container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        pointer-events: none;
      `;
      document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
      const toast = createElement('div', `toast toast-${type} fade-in`);
      toast.style.cssText = `
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        padding: 16px 20px;
        margin-bottom: 12px;
        max-width: 400px;
        pointer-events: auto;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        border-left: 4px solid ${this.getTypeColor(type)};
      `;

      const icon = this.getTypeIcon(type);
      toast.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 12px;">
          <div style="color: ${this.getTypeColor(type)}; font-size: 18px; margin-top: 2px;">
            ${icon}
          </div>
          <div style="flex: 1; color: #374151; font-size: 14px; line-height: 1.5;">
            ${message}
          </div>
          <button class="toast-close" style="
            background: none;
            border: none;
            color: #9ca3af;
            cursor: pointer;
            font-size: 18px;
            padding: 0;
            margin-left: 8px;
          ">×</button>
        </div>
      `;

      this.container.appendChild(toast);
      this.toasts.push(toast);

      // 显示动画
      requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
      });

      // 关闭按钮事件
      const closeBtn = toast.querySelector('.toast-close');
      closeBtn.addEventListener('click', () => this.hide(toast));

      // 自动关闭
      if (duration > 0) {
        setTimeout(() => this.hide(toast), duration);
      }

      return toast;
    }

    hide(toast) {
      if (!toast || !toast.parentNode) return;
      
      toast.style.transform = 'translateX(100%)';
      toast.style.opacity = '0';
      
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
        const index = this.toasts.indexOf(toast);
        if (index > -1) {
          this.toasts.splice(index, 1);
        }
      }, CONFIG.ANIMATION_DURATION);
    }

    getTypeColor(type) {
      const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
      };
      return colors[type] || colors.info;
    }

    getTypeIcon(type) {
      const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
      };
      return icons[type] || icons.info;
    }
  }

  // ==================== 表单增强 ====================
  
  class FormEnhancer {
    constructor() {
      this.init();
    }

    init() {
      this.enhanceFileInputs();
      this.enhanceFormValidation();
      this.enhanceFormSubmission();
      this.addFormAnimations();
    }

    enhanceFileInputs() {
      document.querySelectorAll('input[type="file"]').forEach(input => {
        const wrapper = createElement('div', 'file-upload');
        const label = createElement('label', 'file-upload-label');
        
        label.innerHTML = `
          <i class="bi bi-cloud-upload"></i>
          <span class="file-text">点击选择文件或拖拽到此处</span>
        `;
        
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(label);
        
        input.className = 'file-upload-input';
        
        // 文件选择事件
        input.addEventListener('change', (e) => {
          const file = e.target.files[0];
          const textSpan = label.querySelector('.file-text');
          
          if (file) {
            textSpan.textContent = `已选择: ${file.name}`;
            wrapper.classList.add('has-file');
          } else {
            textSpan.textContent = '点击选择文件或拖拽到此处';
            wrapper.classList.remove('has-file');
          }
        });

        // 拖拽事件
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          label.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
          });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
          label.addEventListener(eventName, () => {
            wrapper.classList.add('drag-over');
          });
        });

        ['dragleave', 'drop'].forEach(eventName => {
          label.addEventListener(eventName, () => {
            wrapper.classList.remove('drag-over');
          });
        });

        label.addEventListener('drop', (e) => {
          const files = e.dataTransfer.files;
          if (files.length > 0) {
            input.files = files;
            input.dispatchEvent(new Event('change'));
          }
        });
      });
    }

    enhanceFormValidation() {
      document.querySelectorAll('input, textarea, select').forEach(field => {
        field.addEventListener('blur', () => this.validateField(field));
        field.addEventListener('input', debounce(() => this.validateField(field), 500));
      });
    }

    validateField(field) {
      const value = field.value.trim();
      const isRequired = field.hasAttribute('required');
      const type = field.type;
      
      // 清除之前的错误状态
      field.classList.remove('error');
      this.removeFieldError(field);
      
      // 必填验证
      if (isRequired && !value) {
        this.showFieldError(field, '此字段为必填项');
        return false;
      }
      
      // 类型验证
      if (value) {
        if (type === 'email' && !this.isValidEmail(value)) {
          this.showFieldError(field, '请输入有效的邮箱地址');
          return false;
        }
        
        if (type === 'number' && isNaN(value)) {
          this.showFieldError(field, '请输入有效的数字');
          return false;
        }
      }
      
      return true;
    }

    showFieldError(field, message) {
      field.classList.add('error');
      
      let errorElement = field.parentNode.querySelector('.form-error');
      if (!errorElement) {
        errorElement = createElement('div', 'form-error');
        field.parentNode.appendChild(errorElement);
      }
      
      errorElement.textContent = message;
    }

    removeFieldError(field) {
      const errorElement = field.parentNode.querySelector('.form-error');
      if (errorElement) {
        errorElement.remove();
      }
    }

    isValidEmail(email) {
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return re.test(email);
    }

    enhanceFormSubmission() {
      document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
          const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
          
          if (submitBtn) {
            // 防止重复提交
            if (submitBtn.disabled) {
              e.preventDefault();
              return;
            }
            
            // 显示加载状态
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
              <div class="loading-spinner" style="width: 16px; height: 16px; margin-right: 8px;"></div>
              处理中...
            `;
            
            // 如果表单验证失败，恢复按钮状态
            setTimeout(() => {
              if (!form.checkValidity()) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
              }
            }, 100);
          }
        });
      });
    }

    addFormAnimations() {
      // 为表单元素添加进入动画
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
          }
        });
      });

      document.querySelectorAll('.form-modern, .form-section').forEach(el => {
        observer.observe(el);
      });
    }
  }

  // ==================== 进度指示器 ====================
  
  class ProgressIndicator {
    constructor(container) {
      this.container = container;
      this.progressBar = null;
      this.init();
    }

    init() {
      this.progressBar = createElement('div', 'progress-bar');
      this.progressBar.innerHTML = '<div class="progress-fill"></div>';
      this.progressBar.style.display = 'none';
      
      if (this.container) {
        this.container.appendChild(this.progressBar);
      }
    }

    show() {
      if (this.progressBar) {
        this.progressBar.style.display = 'block';
        this.setProgress(0);
      }
    }

    hide() {
      if (this.progressBar) {
        this.progressBar.style.display = 'none';
      }
    }

    setProgress(percent) {
      const fill = this.progressBar?.querySelector('.progress-fill');
      if (fill) {
        fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
      }
    }
  }

  // ==================== 键盘快捷键 ====================
  
  class KeyboardShortcuts {
    constructor() {
      this.shortcuts = new Map();
      this.init();
    }

    init() {
      document.addEventListener('keydown', (e) => this.handleKeydown(e));
      
      // 注册默认快捷键
      this.register('ctrl+s', (e) => {
        e.preventDefault();
        const form = document.querySelector('form');
        if (form) {
          form.dispatchEvent(new Event('submit'));
        }
      });

      this.register('escape', () => {
        // 关闭模态框或清除搜索
        const modal = document.querySelector('.modal.show');
        if (modal) {
          modal.classList.remove('show');
        }
        
        const searchInput = document.querySelector('#navSearch');
        if (searchInput && searchInput.value) {
          searchInput.value = '';
          searchInput.dispatchEvent(new Event('input'));
        }
      });
    }

    register(shortcut, callback) {
      this.shortcuts.set(shortcut.toLowerCase(), callback);
    }

    handleKeydown(e) {
      const key = this.getKeyString(e);
      const callback = this.shortcuts.get(key);
      
      if (callback) {
        callback(e);
      }
    }

    getKeyString(e) {
      const parts = [];
      
      if (e.ctrlKey) parts.push('ctrl');
      if (e.altKey) parts.push('alt');
      if (e.shiftKey) parts.push('shift');
      if (e.metaKey) parts.push('meta');
      
      const key = e.key.toLowerCase();
      if (key !== 'control' && key !== 'alt' && key !== 'shift' && key !== 'meta') {
        parts.push(key);
      }
      
      return parts.join('+');
    }
  }

  // ==================== 初始化 ====================
  
  class UIEnhancements {
    constructor() {
      this.loading = new LoadingManager();
      this.toast = new ToastManager();
      this.formEnhancer = new FormEnhancer();
      this.shortcuts = new KeyboardShortcuts();
      
      this.init();
    }

    init() {
      // 等待DOM加载完成
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.onReady());
      } else {
        this.onReady();
      }
    }

    onReady() {
      // 添加全局样式类
      document.body.classList.add('ui-enhanced');
      
      // 处理现有的成功/错误消息
      this.handleExistingMessages();
      
      // 增强现有表单
      this.enhanceExistingForms();
      
      // 添加全局事件监听
      this.addGlobalListeners();
      
      console.log('UI Enhancements initialized');
    }

    handleExistingMessages() {
      // 处理Django消息
      document.querySelectorAll('.alert').forEach(alert => {
        const type = this.getAlertType(alert);
        const message = alert.textContent.trim();
        
        if (message) {
          setTimeout(() => {
            this.toast.show(message, type);
            alert.style.display = 'none';
          }, 500);
        }
      });
    }

    getAlertType(alert) {
      if (alert.classList.contains('alert-success')) return 'success';
      if (alert.classList.contains('alert-danger')) return 'error';
      if (alert.classList.contains('alert-warning')) return 'warning';
      return 'info';
    }

    enhanceExistingForms() {
      // 为现有表单添加现代化样式
      document.querySelectorAll('form').forEach(form => {
        if (!form.classList.contains('form-modern')) {
          form.classList.add('form-modern', 'fade-in');
        }
      });

      // 为现有输入框添加样式
      document.querySelectorAll('input, textarea, select').forEach(field => {
        if (!field.classList.contains('form-input')) {
          field.classList.add('form-input');
        }
      });

      // 为现有按钮添加样式
      document.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(btn => {
        if (!btn.classList.contains('btn')) {
          btn.classList.add('btn', 'btn-primary');
        }
      });
    }

    addGlobalListeners() {
      // 监听AJAX请求
      const originalFetch = window.fetch;
      window.fetch = (...args) => {
        this.loading.show();
        return originalFetch(...args)
          .then(response => {
            this.loading.hide();
            return response;
          })
          .catch(error => {
            this.loading.hide();
            this.toast.show('网络请求失败，请重试', 'error');
            throw error;
          });
      };

      // 监听表单提交错误
      window.addEventListener('error', (e) => {
        console.error('Global error:', e.error);
        this.toast.show('发生了一个错误，请重试', 'error');
      });
    }

    // 公开API
    showLoading(message) {
      this.loading.show(message);
    }

    hideLoading() {
      this.loading.hide();
    }

    showToast(message, type, duration) {
      return this.toast.show(message, type, duration);
    }

    createProgress(container) {
      return new ProgressIndicator(container);
    }
  }

  // ==================== 全局暴露 ====================
  
  window.UIEnhancements = UIEnhancements;
  
  // 自动初始化
  window.ui = new UIEnhancements();

})();