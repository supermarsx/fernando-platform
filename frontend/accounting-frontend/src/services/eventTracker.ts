/**
 * User Interaction Event Tracking Service
 * Tracks clicks, form submissions, navigation, and other user interactions
 */

import telemetryService from './telemetryService';

export interface InteractionEvent {
  type: string;
  element?: string;
  target?: string;
  coordinates?: { x: number; y: number };
  timestamp: number;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface FormEvent {
  formId?: string;
  action: 'submit' | 'change' | 'validation_error' | 'field_focus' | 'field_blur';
  fieldName?: string;
  fieldType?: string;
  value?: string;
  isValid?: boolean;
  errorMessage?: string;
  timestamp: number;
}

export interface NavigationEvent {
  from: string;
  to: string;
  type: 'link' | 'button' | 'direct' | 'back' | 'forward';
  trigger?: string;
  timestamp: number;
}

export interface FeatureUsageEvent {
  feature: string;
  action: 'open' | 'close' | 'use' | 'complete' | 'abandon';
  context?: string;
  duration?: number;
  result?: 'success' | 'failure' | 'cancelled';
  metadata?: Record<string, any>;
  timestamp: number;
}

class EventTracker {
  private trackedElements = new Set<string>();
  private formSubmissions = new Map<string, number>();
  private featureUsage = new Map<string, number>();
  private pageStartTime = Date.now();
  private isEnabled: boolean = true;

  constructor() {
    this.setupGlobalEventListeners();
    this.setupIntersectionObserver();
    this.setupVisibilityObserver();
  }

  /**
   * Setup global event listeners for common interactions
   */
  private setupGlobalEventListeners(): void {
    // Track clicks on interactive elements
    document.addEventListener('click', (event) => {
      if (!this.isEnabled) return;
      
      const target = event.target as HTMLElement;
      if (target) {
        this.trackClick(target, event);
      }
    }, { capture: true });

    // Track form submissions
    document.addEventListener('submit', (event) => {
      if (!this.isEnabled) return;
      
      const form = event.target as HTMLFormElement;
      if (form) {
        this.trackFormSubmission(form, event);
      }
    });

    // Track form field interactions
    document.addEventListener('input', (event) => {
      if (!this.isEnabled) return;
      
      const target = event.target as HTMLInputElement;
      if (target && target.form) {
        this.trackFormFieldChange(target, event);
      }
    });

    document.addEventListener('focus', (event) => {
      if (!this.isEnabled) return;
      
      const target = event.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        this.trackFormFieldFocus(target as HTMLInputElement);
      }
    }, { capture: true });

    document.addEventListener('blur', (event) => {
      if (!this.isEnabled) return;
      
      const target = event.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        this.trackFormFieldBlur(target as HTMLInputElement);
      }
    }, { capture: true });

    // Track scroll events (debounced)
    let scrollTimeout: NodeJS.Timeout;
    document.addEventListener('scroll', () => {
      if (!this.isEnabled) return;
      
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        this.trackScroll();
      }, 500);
    }, { passive: true });

    // Track keyboard shortcuts
    document.addEventListener('keydown', (event) => {
      if (!this.isEnabled) return;
      
      this.trackKeyboardShortcut(event);
    });

    // Track page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (!this.isEnabled) return;
      
      if (document.hidden) {
        this.trackPageHidden();
      } else {
        this.trackPageVisible();
      }
    });
  }

  /**
   * Setup intersection observer to track element visibility
   */
  private setupIntersectionObserver(): void {
    if (!('IntersectionObserver' in window)) {
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          this.trackElementVisible(entry.target as HTMLElement);
        }
      });
    }, {
      threshold: 0.1, // 10% visible
    });

    // Observe common interactive elements
    const selectors = [
      '[data-track]',
      '.clickable',
      'button',
      'a[href]',
      '.nav-item',
      '.menu-item',
      '[role="button"]',
    ];

    selectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((element) => {
        const htmlElement = element as HTMLElement;
        const elementId = this.getElementId(htmlElement);
        if (!this.trackedElements.has(elementId)) {
          observer.observe(htmlElement);
          this.trackedElements.add(elementId);
        }
      });
    });
  }

  /**
   * Setup visibility observer for engagement tracking
   */
  private setupVisibilityObserver(): void {
    if (!('VisibilityState' in document)) return;

    let visibleStartTime = Date.now();
    
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        const visibleDuration = Date.now() - visibleStartTime;
        this.trackEngagement('hidden', visibleDuration);
      } else {
        visibleStartTime = Date.now();
      }
    });
  }

  /**
   * Track clicks on elements
   */
  private trackClick(target: HTMLElement, event: MouseEvent): void {
    const elementId = this.getElementId(target);
    const elementType = this.getElementType(target);
    const context = this.getElementContext(target);

    telemetryService.trackAction('click', elementId, {
      elementType,
      context,
      coordinates: {
        x: event.clientX,
        y: event.clientY,
      },
      page: window.location.pathname,
      timestamp: event.timeStamp,
      tagName: target.tagName,
      classes: target.className,
      textContent: this.getElementText(target),
    });

    // Track specific button types
    if (target.tagName === 'BUTTON') {
      const button = target as HTMLButtonElement;
      this.trackButtonClick(button);
    }

    // Track link clicks
    if (target.tagName === 'A' && (target as HTMLAnchorElement).href) {
      this.trackLinkClick(target as HTMLAnchorElement);
    }
  }

  /**
   * Track form submissions
   */
  private trackFormSubmission(form: HTMLFormElement, event: Event): void {
    const formId = form.id || this.generateFormId(form);
    const formData = this.extractFormData(form);
    
    this.formSubmissions.set(formId, (this.formSubmissions.get(formId) || 0) + 1);

    telemetryService.trackAction('form_submit', formId, {
      formId,
      action: 'submit',
      fieldCount: form.elements.length,
      filledFields: Object.keys(formData).length,
      page: window.location.pathname,
      formMethod: form.method,
      formAction: form.action,
      timestamp: event.timeStamp,
      duration: Date.now() - (this.formSubmissions.get(formId) || 0),
    });

    // Track as a conversion if it's a significant form
    if (this.isImportantForm(form)) {
      telemetryService.trackConversion('form_submission', 1, {
        formId,
        formType: this.getFormType(form),
      });
    }
  }

  /**
   * Track form field changes
   */
  private trackFormFieldChange(field: HTMLInputElement, event: Event): void {
    const formId = field.form?.id || 'unknown';
    const fieldType = field.type || 'text';

    telemetryService.trackAction('form_change', formId, {
      action: 'change',
      formId,
      fieldName: field.name,
      fieldType,
      fieldId: field.id,
      valueLength: field.value.length,
      hasValue: field.value.length > 0,
      timestamp: (event as InputEvent).timeStamp,
    });
  }

  /**
   * Track form field focus
   */
  private trackFormFieldFocus(field: HTMLInputElement): void {
    const formId = field.form?.id || 'unknown';
    
    telemetryService.trackAction('form_focus', formId, {
      action: 'field_focus',
      formId,
      fieldName: field.name,
      fieldType: field.type,
      fieldId: field.id,
      timestamp: Date.now(),
    });
  }

  /**
   * Track form field blur
   */
  private trackFormFieldBlur(field: HTMLInputElement): void {
    const formId = field.form?.id || 'unknown';
    
    telemetryService.trackAction('form_blur', formId, {
      action: 'field_blur',
      formId,
      fieldName: field.name,
      fieldType: field.type,
      fieldId: field.id,
      timestamp: Date.now(),
    });
  }

  /**
   * Track button clicks specifically
   */
  private trackButtonClick(button: HTMLButtonElement): void {
    const buttonType = button.type || 'submit';
    const isPrimary = button.classList.contains('primary') || 
                     button.classList.contains('btn-primary');

    telemetryService.trackFeatureUsage('button_click', {
      buttonType,
      isPrimary,
      buttonText: this.getElementText(button),
      buttonId: button.id,
      buttonClasses: button.className,
    });
  }

  /**
   * Track link clicks
   */
  private trackLinkClick(link: HTMLAnchorElement): void {
    const href = link.href;
    const isExternal = href.startsWith('http') && !href.includes(window.location.host);
    const linkText = this.getElementText(link);

    telemetryService.trackAction('link_click', href, {
      linkText,
      isExternal,
      href,
      target: link.target,
      rel: link.rel,
      linkType: this.getLinkType(href),
    });

    // Track navigation if it's an internal link
    if (!isExternal) {
      const navigationEvent: NavigationEvent = {
        from: window.location.pathname,
        to: new URL(href).pathname,
        type: 'link',
        trigger: linkText,
        timestamp: Date.now(),
      };
      
      this.trackNavigation(navigationEvent);
    }
  }

  /**
   * Track scroll behavior
   */
  private trackScroll(): void {
    const scrollTop = window.pageYOffset;
    const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrollPercentage = (scrollTop / documentHeight) * 100;

    telemetryService.trackAction('scroll', 'page', {
      scrollTop,
      scrollPercentage: Math.round(scrollPercentage),
      scrollDirection: this.getScrollDirection(),
      timestamp: Date.now(),
    });

    // Track scroll milestones
    if (scrollPercentage >= 25 && scrollPercentage < 50) {
      telemetryService.trackEngagement('scroll_25');
    } else if (scrollPercentage >= 50 && scrollPercentage < 75) {
      telemetryService.trackEngagement('scroll_50');
    } else if (scrollPercentage >= 75 && scrollPercentage < 90) {
      telemetryService.trackEngagement('scroll_75');
    } else if (scrollPercentage >= 90) {
      telemetryService.trackEngagement('scroll_90');
    }
  }

  /**
   * Track keyboard shortcuts
   */
  private trackKeyboardShortcut(event: KeyboardEvent): void {
    if (event.ctrlKey || event.metaKey || event.altKey) {
      const key = event.key.toLowerCase();
      const modifier = event.ctrlKey ? 'ctrl' : event.metaKey ? 'cmd' : 'alt';
      
      telemetryService.trackAction('keyboard_shortcut', `${modifier}+${key}`, {
        key,
        modifier,
        timestamp: event.timeStamp,
        ctrlKey: event.ctrlKey,
        metaKey: event.metaKey,
        altKey: event.altKey,
        shiftKey: event.shiftKey,
      });
    }
  }

  /**
   * Track page visibility changes
   */
  private trackPageHidden(): void {
    const visibleTime = Date.now() - this.pageStartTime;
    
    telemetryService.trackAction('page_hidden', window.location.pathname, {
      visibleTime,
      timestamp: Date.now(),
    });
  }

  private trackPageVisible(): void {
    this.pageStartTime = Date.now();
    
    telemetryService.trackAction('page_visible', window.location.pathname, {
      timestamp: Date.now(),
    });
  }

  /**
   * Track element visibility
   */
  private trackElementVisible(element: HTMLElement): void {
    const elementId = this.getElementId(element);
    const elementType = this.getElementType(element);

    telemetryService.trackAction('element_visible', elementId, {
      elementType,
      tagName: element.tagName,
      textContent: this.getElementText(element),
      timestamp: Date.now(),
    });
  }

  /**
   * Track engagement metrics
   */
  private trackEngagement(type: string, duration?: number): void {
    telemetryService.trackEvent('engagement', {
      type,
      duration,
      page: window.location.pathname,
      timestamp: Date.now(),
    });
  }

  /**
   * Track feature usage
   */
  public trackFeatureEvent(feature: string, action: FeatureUsageEvent['action'], metadata?: Record<string, any>): void {
    this.featureUsage.set(feature, (this.featureUsage.get(feature) || 0) + 1);

    telemetryService.trackFeatureUsage(feature, {
      action,
      count: this.featureUsage.get(feature),
      timestamp: Date.now(),
      ...metadata,
    });
  }

  /**
   * Track navigation events
   */
  public trackNavigation(event: NavigationEvent): void {
    telemetryService.trackAction('navigation', event.to, {
      from: event.from,
      to: event.to,
      type: event.type,
      trigger: event.trigger,
      timestamp: event.timestamp,
    });
  }

  /**
   * Track user journey progression
   */
  public trackUserJourney(step: string, context?: Record<string, any>): void {
    telemetryService.trackEvent('user_journey', {
      step,
      context,
      timestamp: Date.now(),
      page: window.location.pathname,
    });
  }

  /**
   * Track A/B test variants
   */
  public trackABTest(testName: string, variant: string): void {
    telemetryService.trackEvent('ab_test', {
      testName,
      variant,
      timestamp: Date.now(),
    });
  }

  /**
   * Get element ID for tracking
   */
  private getElementId(element: HTMLElement): string {
    return element.id || 
           element.dataset.track || 
           `${element.tagName.toLowerCase()}_${Array.from(element.classList).join('_')}_${Math.random().toString(36).substr(2, 5)}`;
  }

  /**
   * Get element type for classification
   */
  private getElementType(element: HTMLElement): string {
    if (element.tagName === 'BUTTON') return 'button';
    if (element.tagName === 'A') return 'link';
    if (element.tagName === 'INPUT') return 'input';
    if (element.tagName === 'TEXTAREA') return 'textarea';
    if (element.tagName === 'SELECT') return 'select';
    if (element.getAttribute('role') === 'button') return 'button';
    if (element.classList.contains('clickable')) return 'clickable';
    return element.tagName.toLowerCase();
  }

  /**
   * Get element context (navigation, content, form, etc.)
   */
  private getElementContext(element: HTMLElement): string {
    const nav = element.closest('nav, .nav, .navigation');
    if (nav) return 'navigation';

    const form = element.closest('form');
    if (form) return 'form';

    const modal = element.closest('.modal, [role="dialog"]');
    if (modal) return 'modal';

    const header = element.closest('header, .header');
    if (header) return 'header';

    const footer = element.closest('footer, .footer');
    if (footer) return 'footer';

    const sidebar = element.closest('.sidebar, .side-nav');
    if (sidebar) return 'sidebar';

    return 'content';
  }

  /**
   * Get element text content (truncated)
   */
  private getElementText(element: HTMLElement): string {
    const text = element.textContent?.trim() || '';
    return text.length > 100 ? text.substring(0, 97) + '...' : text;
  }

  /**
   * Generate form ID
   */
  private generateFormId(form: HTMLFormElement): string {
    const action = form.action || 'unknown';
    const method = form.method || 'get';
    return `form_${method}_${action.split('/').pop()}_${Math.random().toString(36).substr(2, 5)}`;
  }

  /**
   * Extract form data (anonymized)
   */
  private extractFormData(form: HTMLFormElement): Record<string, any> {
    const data: Record<string, any> = {};
    
    Array.from(form.elements).forEach((element) => {
      const input = element as HTMLInputElement;
      if (input.name && !input.type.match(/password|hidden/)) {
        data[input.name] = input.value ? '[FILLED]' : '[EMPTY]';
      }
    });

    return data;
  }

  /**
   * Check if form is important (for conversion tracking)
   */
  private isImportantForm(form: HTMLFormElement): boolean {
    const importantKeywords = ['login', 'register', 'signup', 'checkout', 'contact', 'subscription'];
    const formText = form.textContent?.toLowerCase() || '';
    
    return importantKeywords.some(keyword => formText.includes(keyword));
  }

  /**
   * Get form type classification
   */
  private getFormType(form: HTMLFormElement): string {
    const action = form.action.toLowerCase();
    const formText = form.textContent?.toLowerCase() || '';
    
    if (action.includes('login') || formText.includes('login')) return 'login';
    if (action.includes('register') || formText.includes('register')) return 'register';
    if (action.includes('contact') || formText.includes('contact')) return 'contact';
    if (action.includes('checkout')) return 'checkout';
    
    return 'general';
  }

  /**
   * Get link type classification
   */
  private getLinkType(href: string): string {
    const url = new URL(href, window.location.origin);
    
    if (href.startsWith('mailto:')) return 'email';
    if (href.startsWith('tel:')) return 'phone';
    if (href.startsWith('#')) return 'anchor';
    if (url.pathname.includes('/admin/')) return 'admin';
    if (url.pathname.includes('/billing/')) return 'billing';
    
    return 'general';
  }

  /**
   * Get current scroll direction
   */
  private getScrollDirection(): 'up' | 'down' {
    const currentScroll = window.pageYOffset;
    // This is simplified - in a real implementation, you'd track the previous position
    return 'down';
  }

  /**
   * Enable/disable event tracking
   */
  public setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  /**
   * Get tracking statistics
   */
  public getTrackingStats() {
    return {
      trackedElements: this.trackedElements.size,
      formSubmissions: Object.fromEntries(this.formSubmissions),
      featureUsage: Object.fromEntries(this.featureUsage),
      sessionStart: this.pageStartTime,
    };
  }

  /**
   * Clear tracking data
   */
  public clearData(): void {
    this.trackedElements.clear();
    this.formSubmissions.clear();
    this.featureUsage.clear();
    this.pageStartTime = Date.now();
  }

  /**
   * Clean up
   */
  public destroy(): void {
    this.isEnabled = false;
    this.clearData();
  }
}

// Create singleton instance
const eventTracker = new EventTracker();

export default eventTracker;
