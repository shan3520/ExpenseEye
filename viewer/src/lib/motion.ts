import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { CustomEase } from 'gsap/CustomEase';

// Register once on first import. Both plugins ship free with gsap 3.11+.
gsap.registerPlugin(ScrollTrigger, CustomEase);

/**
 * The motion system's standard easing — cubic-bezier(0.32, 0.72, 0, 1). A
 * fast-out / long-settle curve that reads as spring/mass without bounce. Used
 * for every entrance and scroll reveal.
 */
export const STANDARD_EASE = CustomEase.create('ee-standard', '0.32,0.72,0,1');

/**
 * A deliberate slight-overshoot curve — cubic-bezier(0.34, 1.56, 0.64, 1). Used
 * only where a small bounce is functional (the drop-zone releasing), never
 * decoratively.
 */
export const SPRING_EASE = CustomEase.create('ee-spring', '0.34,1.56,0.64,1');

export { gsap, ScrollTrigger };
