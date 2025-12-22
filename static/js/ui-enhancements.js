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

// ==================== 表单实时验证增强 ====================

class AdvancedFormValidator {
  constructor() {
    this.rules = new Map();
    this.init();
  }

  init() {
    // 注册默认验证规则
    this.registerRule('required', (value) => {
      return value.trim() !== '';
    }, '此字段为必填项');

    this.registerRule('email', (value) => {
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return re.test(value);
    }, '请输入有效的邮箱地址');

    this.registerRule('number', (value) => {
      return !isNaN(value) && isFinite(value);
    }, '请输入有效的数字');

    this.registerRule('minLength', (value, min) => {
      return value.length >= min;
    }, '输入长度不足');

    this.registerRule('maxLength', (value, max) => {
      return value.length <= max;
    }, '输入长度超限');

    this.registerRule('pattern', (value, pattern) => {
      const regex = new RegExp(pattern);
      return regex.test(value);
    }, '格式不正确');

    // 监听所有表单字段
    this.attachValidators();
  }

  registerRule(name, validator, message) {
    this.rules.set(name, { validator, message });
  }

  attachValidators() {
    document.addEventListener('input', (e) => {
      if (e.target.matches('input, textarea, select')) {
        this.validateFieldRealtime(e.target);
      }
    });

    document.addEventListener('blur', (e) => {
      if (e.target.matches('input, textarea, select')) {
        this.validateField(e.target);
      }
    }, true);
  }

  validateFieldRealtime(field) {
    // 实时验证（输入时）- 只显示成功状态，不显示错误
    if (this.isFieldValid(field)) {
      this.showFieldSuccess(field);
    } else {
      this.clearFieldStatus(field);
    }
  }

  validateField(field) {
    // 完整验证（失焦时）- 显示错误和成功状态
    if (this.isFieldValid(field)) {
      this.showFieldSuccess(field);
      return true;
    } else {
      const errors = this.getFieldErrors(field);
      if (errors.length > 0) {
        this.showFieldError(field, errors[0]);
      }
      return false;
    }
  }

  isFieldValid(field) {
    const errors = this.getFieldErrors(field);
    return errors.length === 0;
  }

  getFieldErrors(field) {
    const errors = [];
    const value = field.value.trim();

    // 必填验证
    if (field.hasAttribute('required') && !value) {
      errors.push('此字段为必填项');
      return errors; // 如果必填验证失败，不进行其他验证
    }

    // 只有在有值的情况下才进行其他验证
    if (value) {
      // 类型验证
      if (field.type === 'email' && !this.rules.get('email').validator(value)) {
        errors.push(this.rules.get('email').message);
      }

      if (field.type === 'number' && !this.rules.get('number').validator(value)) {
        errors.push(this.rules.get('number').message);
      }

      // 长度验证
      const minLength = field.getAttribute('minlength');
      if (minLength && !this.rules.get('minLength').validator(value, parseInt(minLength))) {
        errors.push(`至少需要 ${minLength} 个字符`);
      }

      const maxLength = field.getAttribute('maxlength');
      if (maxLength && !this.rules.get('maxLength').validator(value, parseInt(maxLength))) {
        errors.push(`最多允许 ${maxLength} 个字符`);
      }

      // 模式验证
      const pattern = field.getAttribute('pattern');
      if (pattern && !this.rules.get('pattern').validator(value, pattern)) {
        errors.push(field.getAttribute('title') || this.rules.get('pattern').message);
      }
    }

    return errors;
  }

  showFieldError(field, message) {
    this.clearFieldStatus(field);
    field.classList.add('is-invalid');
    
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    
    field.parentNode.appendChild(feedback);
  }

  showFieldSuccess(field) {
    this.clearFieldStatus(field);
    field.classList.add('is-valid');
    
    const feedback = document.createElement('div');
    feedback.className = 'valid-feedback';
    feedback.innerHTML = '<i class="bi bi-check-circle"></i> 输入正确';
    
    field.parentNode.appendChild(feedback);
  }

  clearFieldStatus(field) {
    field.classList.remove('is-invalid', 'is-valid');
    
    const feedbacks = field.parentNode.querySelectorAll('.invalid-feedback, .valid-feedback');
    feedbacks.forEach(feedback => feedback.remove());
  }

  validateForm(form) {
    let isValid = true;
    const fields = form.querySelectorAll('input, textarea, select');
    
    fields.forEach(field => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });

    return isValid;
  }
}

// ==================== 状态消息管理 ====================

class StatusMessageManager {
  constructor() {
    this.container = null;
    this.init();
  }

  init() {
    this.container = document.createElement('div');
    this.container.className = 'status-messages';
    this.container.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      z-index: 1050;
      max-width: 400px;
    `;
    document.body.appendChild(this.container);
  }

  show(message, type = 'info', duration = 5000) {
    const messageEl = document.createElement('div');
    messageEl.className = `alert alert-${type} alert-dismissible fade show`;
    messageEl.style.cssText = `
      margin-bottom: 10px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      border: none;
      border-radius: 8px;
    `;

    const icon = this.getIcon(type);
    messageEl.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 18px;">${icon}</span>
        <span style="flex: 1;">${message}</span>
        <button type="button" class="btn-close" aria-label="关闭"></button>
      </div>
    `;

    this.container.appendChild(messageEl);

    // 关闭按钮事件
    const closeBtn = messageEl.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => this.hide(messageEl));

    // 自动关闭
    if (duration > 0) {
      setTimeout(() => this.hide(messageEl), duration);
    }

    return messageEl;
  }

  hide(messageEl) {
    if (messageEl && messageEl.parentNode) {
      messageEl.style.opacity = '0';
      messageEl.style.transform = 'translateX(100%)';
      
      setTimeout(() => {
        if (messageEl.parentNode) {
          messageEl.parentNode.removeChild(messageEl);
        }
      }, 300);
    }
  }

  getIcon(type) {
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    return icons[type] || icons.info;
  }
}

// ==================== 键盘导航增强 ====================

class KeyboardNavigationEnhancer {
  constructor() {
    this.focusableElements = [
      'input:not([disabled])',
      'textarea:not([disabled])',
      'select:not([disabled])',
      'button:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])'
    ].join(', ');
    
    this.init();
  }

  init() {
    this.enhanceFocusVisibility();
    this.addKeyboardShortcuts();
    this.improveTabNavigation();
  }

  enhanceFocusVisibility() {
    // 为所有可聚焦元素添加焦点样式
    document.addEventListener('focusin', (e) => {
      if (e.target.matches(this.focusableElements)) {
        e.target.classList.add('focus-visible');
      }
    });

    document.addEventListener('focusout', (e) => {
      e.target.classList.remove('focus-visible');
    });

    // 鼠标点击时移除焦点样式
    document.addEventListener('mousedown', (e) => {
      if (e.target.matches(this.focusableElements)) {
        e.target.classList.add('mouse-focus');
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        document.querySelectorAll('.mouse-focus').forEach(el => {
          el.classList.remove('mouse-focus');
        });
      }
    });
  }

  addKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Alt + 数字键快速导航到表单字段
      if (e.altKey && e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        const inputs = document.querySelectorAll('input, textarea, select');
        if (inputs[index]) {
          inputs[index].focus();
        }
      }

      // Ctrl + Enter 提交表单
      if (e.ctrlKey && e.key === 'Enter') {
        const form = e.target.closest('form');
        if (form) {
          e.preventDefault();
          form.dispatchEvent(new Event('submit'));
        }
      }

      // F1 显示帮助信息
      if (e.key === 'F1') {
        e.preventDefault();
        this.showKeyboardHelp();
      }
    });
  }

  improveTabNavigation() {
    // 改善表格中的Tab导航
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab' && e.target.closest('table')) {
        const table = e.target.closest('table');
        const focusableInTable = table.querySelectorAll(this.focusableElements);
        const currentIndex = Array.from(focusableInTable).indexOf(e.target);
        
        if (e.shiftKey) {
          // Shift + Tab - 向前导航
          if (currentIndex === 0) {
            e.preventDefault();
            focusableInTable[focusableInTable.length - 1].focus();
          }
        } else {
          // Tab - 向后导航
          if (currentIndex === focusableInTable.length - 1) {
            e.preventDefault();
            focusableInTable[0].focus();
          }
        }
      }
    });
  }

  showKeyboardHelp() {
    const helpContent = `
      <div style="padding: 20px; max-width: 500px;">
        <h4 style="margin-bottom: 16px;">键盘快捷键</h4>
        <div style="display: grid; gap: 8px; font-size: 14px;">
          <div><kbd>Ctrl + S</kbd> 保存表单</div>
          <div><kbd>Ctrl + Enter</kbd> 提交表单</div>
          <div><kbd>Alt + 1-9</kbd> 快速导航到表单字段</div>
          <div><kbd>Tab</kbd> / <kbd>Shift + Tab</kbd> 在字段间导航</div>
          <div><kbd>Escape</kbd> 关闭弹窗或清除搜索</div>
          <div><kbd>F1</kbd> 显示此帮助</div>
        </div>
      </div>
    `;

    if (window.ui && window.ui.toast) {
      window.ui.toast.show(helpContent, 'info', 8000);
    }
  }
}

// ==================== 增强初始化 ====================

// 扩展现有的UIEnhancements类
if (window.ui) {
  // 添加新的增强功能
  window.ui.validator = new AdvancedFormValidator();
  window.ui.statusMessages = new StatusMessageManager();
  window.ui.keyboardNav = new KeyboardNavigationEnhancer();

  // 扩展公开API
  window.ui.showStatus = function(message, type, duration) {
    return this.statusMessages.show(message, type, duration);
  };

  window.ui.validateForm = function(form) {
    return this.validator.validateForm(form);
  };

  console.log('Advanced UI Enhancements loaded');
}

// ==================== CSS样式注入 ====================

const enhancedStyles = `
<style>
/* 表单验证状态样式 */
.form-control.is-valid {
  border-color: var(--success-color, #10b981);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-control.is-invalid {
  border-color: var(--error-color, #ef4444);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.valid-feedback {
  display: block;
  width: 100%;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: var(--success-color, #10b981);
}

.invalid-feedback {
  display: block;
  width: 100%;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: var(--error-color, #ef4444);
}

/* 焦点可见性增强 */
.focus-visible:not(.mouse-focus) {
  outline: 2px solid var(--primary-color, #667eea) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2) !important;
}

/* 键盘导航提示 */
kbd {
  display: inline-block;
  padding: 2px 6px;
  font-size: 11px;
  line-height: 1.4;
  color: #495057;
  background-color: #f8f9fa;
  border: 1px solid #adb5bd;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

/* 状态消息动画 */
.alert {
  transition: all 0.3s ease;
}

.alert.fade.show {
  opacity: 1;
  transform: translateX(0);
}

/* 文件上传拖拽状态 */
.file-upload.drag-over .file-upload-label {
  border-color: var(--primary-color, #667eea);
  background-color: rgba(102, 126, 234, 0.1);
  transform: scale(1.02);
}

/* 加载状态按钮 */
.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn .loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式表格 */
@media (max-width: 768px) {
  .table-responsive {
    overflow-x: auto;
  }
  
  .table-responsive table {
    min-width: 600px;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .focus-visible:not(.mouse-focus) {
    outline: 3px solid #000 !important;
    outline-offset: 2px !important;
  }
}

/* 减少动画模式支持 */
@media (prefers-reduced-motion: reduce) {
  .alert,
  .file-upload-label,
  .btn {
    transition: none !important;
  }
  
  .loading-spinner {
    animation: none !important;
  }
}
</style>
`;

// 注入样式
if (!document.querySelector('#enhanced-ui-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'enhanced-ui-styles';
  styleElement.innerHTML = enhancedStyles;
  document.head.appendChild(styleElement);
}

// ==================== 中文本地化支持 ====================

class ChineseLocalization {
  constructor() {
    this.messages = {
      // 通用消息
      loading: '加载中...',
      saving: '保存中...',
      processing: '处理中...',
      success: '操作成功',
      error: '操作失败',
      warning: '警告',
      info: '提示',
      
      // 操作消息
      confirm: '确认操作',
      cancel: '取消',
      delete: '删除',
      edit: '编辑',
      add: '添加',
      save: '保存',
      submit: '提交',
      reset: '重置',
      search: '搜索',
      filter: '筛选',
      refresh: '刷新',
      back: '返回',
      close: '关闭',
      
      // 状态消息
      enable: '启用',
      disable: '禁用',
      active: '激活',
      inactive: '未激活',
      online: '在线',
      offline: '离线',
      
      // 表单验证消息
      required: '此字段为必填项',
      invalid_email: '请输入有效的邮箱地址',
      invalid_number: '请输入有效的数字',
      invalid_url: '请输入有效的网址',
      invalid_phone: '请输入有效的手机号码',
      min_length: '输入长度不足，至少需要 {min} 个字符',
      max_length: '输入长度超限，最多允许 {max} 个字符',
      pattern_mismatch: '输入格式不正确',
      
      // 文件上传消息
      file_select: '点击选择文件或拖拽到此处',
      file_selected: '已选择文件: {filename}',
      file_upload_success: '文件上传成功',
      file_upload_error: '文件上传失败',
      file_too_large: '文件大小超过限制',
      file_type_invalid: '文件类型不支持',
      
      // 网络消息
      network_error: '网络连接失败，请检查网络后重试',
      server_error: '服务器错误，请稍后重试',
      timeout_error: '请求超时，请重试',
      
      // 确认对话框
      delete_confirm: '确定要删除这个项目吗？此操作不可撤销。',
      unsaved_changes: '您有未保存的更改，确定要离开吗？',
      
      // 键盘快捷键
      keyboard_shortcuts: '键盘快捷键',
      shortcut_save: '保存表单',
      shortcut_submit: '提交表单',
      shortcut_navigate: '快速导航到表单字段',
      shortcut_tab: '在字段间导航',
      shortcut_escape: '关闭弹窗或清除搜索',
      shortcut_help: '显示此帮助',
      
      // 时间相关
      just_now: '刚刚',
      minutes_ago: '{minutes}分钟前',
      hours_ago: '{hours}小时前',
      days_ago: '{days}天前',
      weeks_ago: '{weeks}周前',
      months_ago: '{months}个月前',
      years_ago: '{years}年前',
      
      // 数据状态
      no_data: '暂无数据',
      loading_data: '正在加载数据...',
      load_more: '加载更多',
      end_of_data: '没有更多数据了',
      
      // 搜索相关
      search_placeholder: '请输入搜索关键词...',
      search_no_results: '未找到匹配的结果',
      search_results: '找到 {count} 个结果',
      
      // 分页相关
      page_info: '第 {current} 页，共 {total} 页',
      items_per_page: '每页显示 {count} 项',
      total_items: '共 {count} 项',
      
      // 操作结果
      save_success: '保存成功',
      save_error: '保存失败',
      delete_success: '删除成功',
      delete_error: '删除失败',
      update_success: '更新成功',
      update_error: '更新失败',
      create_success: '创建成功',
      create_error: '创建失败'
    };
    
    this.dateFormats = {
      full: 'YYYY年MM月DD日 dddd HH:mm:ss',
      date: 'YYYY年MM月DD日',
      time: 'HH:mm:ss',
      short: 'YYYY年MM月DD日 HH:mm',
      month: 'YYYY年MM月',
      year: 'YYYY年'
    };
    
    this.weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    this.months = ['一月', '二月', '三月', '四月', '五月', '六月', 
                   '七月', '八月', '九月', '十月', '十一月', '十二月'];
  }

  getMessage(key, params = {}) {
    let message = this.messages[key] || key;
    
    // 替换参数
    Object.keys(params).forEach(param => {
      message = message.replace(`{${param}}`, params[param]);
    });
    
    return message;
  }

  formatDateTime(date, format = 'full') {
    if (!date) return '';
    
    const d = new Date(date);
    const year = d.getFullYear();
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const hour = d.getHours();
    const minute = d.getMinutes();
    const second = d.getSeconds();
    const weekday = this.weekdays[d.getDay()];
    
    switch (format) {
      case 'full':
        return `${year}年${month}月${day}日 ${weekday} ${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:${second.toString().padStart(2, '0')}`;
      case 'date':
        return `${year}年${month}月${day}日`;
      case 'time':
        return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:${second.toString().padStart(2, '0')}`;
      case 'short':
        return `${year}年${month}月${day}日 ${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
      case 'month':
        return `${year}年${month}月`;
      case 'year':
        return `${year}年`;
      default:
        return d.toLocaleString('zh-CN');
    }
  }

  formatNumber(number, options = {}) {
    if (typeof number !== 'number') return number;
    
    const { 
      useThousandSeparator = true, 
      decimalPlaces = null,
      useChineseDigits = false 
    } = options;
    
    if (useChineseDigits && Number.isInteger(number) && number >= 0 && number <= 99) {
      return this.numberToChinese(number);
    }
    
    let formatted = number.toString();
    
    if (decimalPlaces !== null) {
      formatted = number.toFixed(decimalPlaces);
    }
    
    if (useThousandSeparator) {
      formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, '，');
    }
    
    return formatted;
  }

  numberToChinese(num) {
    const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
    
    if (num === 0) return digits[0];
    if (num < 10) return digits[num];
    if (num === 10) return '十';
    if (num < 20) return `十${digits[num % 10]}`;
    if (num < 100) {
      const tens = Math.floor(num / 10);
      const ones = num % 10;
      return ones === 0 ? `${digits[tens]}十` : `${digits[tens]}十${digits[ones]}`;
    }
    
    return num.toString();
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 字节';
    
    const units = ['字节', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let size = bytes;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return unitIndex === 0 
      ? `${Math.floor(size)} ${units[unitIndex]}`
      : `${size.toFixed(2)} ${units[unitIndex]}`;
  }

  getRelativeTime(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (seconds < 60) return this.getMessage('just_now');
    if (minutes < 60) return this.getMessage('minutes_ago', { minutes });
    if (hours < 24) return this.getMessage('hours_ago', { hours });
    if (days < 7) return this.getMessage('days_ago', { days });
    if (days < 30) return this.getMessage('weeks_ago', { weeks: Math.floor(days / 7) });
    if (days < 365) return this.getMessage('months_ago', { months: Math.floor(days / 30) });
    
    return this.getMessage('years_ago', { years: Math.floor(days / 365) });
  }
}

// 扩展现有的UIEnhancements类
if (window.ui) {
  window.ui.i18n = new ChineseLocalization();
  
  // 更新现有消息为中文
  const originalToast = window.ui.toast;
  if (originalToast) {
    // 重写toast消息，使用中文
    const originalShow = originalToast.show.bind(originalToast);
    originalToast.show = function(message, type = 'info', duration) {
      // 如果消息是英文关键词，尝试翻译
      const translatedMessage = window.ui.i18n.getMessage(message) || message;
      return originalShow(translatedMessage, type, duration);
    };
  }
  
  // 添加中文化的API方法
  window.ui.showChineseMessage = function(key, params, type = 'info', duration) {
    const message = this.i18n.getMessage(key, params);
    return this.showToast(message, type, duration);
  };
  
  window.ui.formatChineseDateTime = function(date, format) {
    return this.i18n.formatDateTime(date, format);
  };
  
  window.ui.formatChineseNumber = function(number, options) {
    return this.i18n.formatNumber(number, options);
  };
  
  console.log('Chinese Localization loaded');
}

// ==================== 中文表单验证消息 ====================

// 更新表单验证器的错误消息
if (window.ui && window.ui.validator) {
  const validator = window.ui.validator;
  
  // 重新注册中文验证规则
  validator.registerRule('required', (value) => {
    return value.trim() !== '';
  }, '此字段为必填项');

  validator.registerRule('email', (value) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(value);
  }, '请输入有效的邮箱地址');

  validator.registerRule('number', (value) => {
    return !isNaN(value) && isFinite(value);
  }, '请输入有效的数字');

  validator.registerRule('phone', (value) => {
    const re = /^1[3-9]\d{9}$/;
    return re.test(value);
  }, '请输入有效的手机号码');

  validator.registerRule('url', (value) => {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  }, '请输入有效的网址');

  validator.registerRule('chinese', (value) => {
    const re = /^[\u4e00-\u9fa5]+$/;
    return re.test(value);
  }, '请输入中文字符');

  validator.registerRule('idCard', (value) => {
    const re = /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/;
    return re.test(value);
  }, '请输入有效的身份证号码');
}

// ==================== 中文日期时间工具 ====================

// 扩展Date原型，添加中文格式化方法
Date.prototype.toChinese = function(format = 'full') {
  if (window.ui && window.ui.i18n) {
    return window.ui.i18n.formatDateTime(this, format);
  }
  return this.toLocaleString('zh-CN');
};

// 扩展Number原型，添加中文格式化方法
Number.prototype.toChinese = function(options = {}) {
  if (window.ui && window.ui.i18n) {
    return window.ui.i18n.formatNumber(this, options);
  }
  return this.toLocaleString('zh-CN');
};

// ==================== 自动中文化现有内容 ====================

document.addEventListener('DOMContentLoaded', function() {
  // 自动翻译常见的英文按钮文本
  const translations = {
    'Save': '保存',
    'Cancel': '取消',
    'Delete': '删除',
    'Edit': '编辑',
    'Add': '添加',
    'Submit': '提交',
    'Reset': '重置',
    'Search': '搜索',
    'Filter': '筛选',
    'Refresh': '刷新',
    'Back': '返回',
    'Next': '下一步',
    'Previous': '上一步',
    'Close': '关闭',
    'Open': '打开',
    'Loading...': '加载中...',
    'Please wait...': '请稍候...',
    'Success': '成功',
    'Error': '错误',
    'Warning': '警告',
    'Info': '信息'
  };
  
  // 翻译按钮文本
  document.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(element => {
    const text = element.textContent.trim();
    if (translations[text]) {
      element.textContent = translations[text];
    }
  });
  
  // 翻译placeholder文本
  document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(element => {
    const placeholder = element.getAttribute('placeholder');
    if (translations[placeholder]) {
      element.setAttribute('placeholder', translations[placeholder]);
    }
  });
  
  // 为日期时间元素添加中文格式
  document.querySelectorAll('[data-datetime]').forEach(element => {
    const datetime = element.getAttribute('data-datetime');
    const format = element.getAttribute('data-format') || 'full';
    
    if (window.ui && window.ui.i18n) {
      element.textContent = window.ui.i18n.formatDateTime(datetime, format);
    }
  });
  
  // 为数字元素添加中文格式
  document.querySelectorAll('[data-number]').forEach(element => {
    const number = parseFloat(element.getAttribute('data-number'));
    const useThousandSeparator = element.hasAttribute('data-thousand-separator');
    
    if (window.ui && window.ui.i18n && !isNaN(number)) {
      element.textContent = window.ui.i18n.formatNumber(number, { useThousandSeparator });
    }
  });
});