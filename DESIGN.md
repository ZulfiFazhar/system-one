# Product Design Specification: TypeSafe AI Homepage

## 1. Overview

This document outlines the design specifications for the TypeSafe AI homepage, focusing on a clean, reusable design system approach. The page aims to introduce TypeSafe AI's mission and product, Jev, highlighting its performance benefits and inviting user engagement.

## 2. Experience Goals

- **Inform:** Clearly communicate TypeSafe AI's unique research direction and product value.
- **Engage:** Encourage users to explore the manifesto, team, documentation, and API console.
- **Convert:** Drive interest in early access and open roles.

## 3. Information Architecture

The page is structured around a hero section, followed by sections detailing product benefits, performance metrics, and calls to action for engagement and careers.

## 4. Layout System

The layout primarily uses a Flexbox model for responsive content arrangement.

- **Alignment:** `align-items: center` is common, with `flex-start` and `flex-end` also used.
- **Justification:** `justify-content: center`, `flex-start`, and `flex-end` are utilized.
- **Positioning:** A mix of `relative`, `absolute`, and `fixed` positioning is present.

## 5. Section-by-Section Design Spec

- **Hero Section:** Features a prominent H1 "We took the opposite research direction" with supporting links and dynamic visual elements.
- **Product Benefits:** Highlights "193.6x Faster, 444.6x Cheaper" and "Jev’s intelligence per dollar is literally off the charts."
- **Call to Action:** "Come Build With Us" and "Open roles" sections.
- **FAQ:** "We give a FAQ" section for common questions.

## 6. Component Inventory

- **Buttons:** Capitalized text, `border-radius: inherit`, `box-shadow: 2px 2px 0px rgba(0,0,0,0.4)`.
- **Cards:** `border: 1px solid #1E1E1E`, `box-shadow: 2px 2px 0px rgba(0,0,0,0.4)`, `border-radius: inherit`.
- **Links:** Standard text links, some with background radius variations.

## 7. Visual Design Specification

### 7.1. Design System Tokens

- **Primary Text Color:** `--color-text-primary: #1E1E1E` (rgb(30, 30, 30))
- **Secondary Text Color:** `--color-text-secondary: #858585e6` (confirm exact value)
- **Background Color:** `--color-background-primary: #fefefe` (rgb(254, 254, 254))
- **Accent Colors:** `--color-accent-pink: #f386a1`, `--color-accent-purple: #d45bb6`, `--color-accent-green: #03aa5c`, `--color-accent-teal: #09aea1`
- **Border Color:** `--color-border-default: #dedede`
- **Shadow:** `--shadow-default: 2px 2px 0px rgba(0,0,0,0.4)`

### 7.2. Typography

- **Font Families:** Host Grotesk, Fragment Mono, JetBrains Mono, Space Mono, Die Grotesk C Medium/Regular, Inter, LisaTerminal Paper 2X3Y Medium, SF Pro Variable Regular. (Confirm usage hierarchy and fallbacks).
- **Base Font Size:** `--framer-font-size: 12px` (confirm for body text).
- **Line Height:** `--framer-line-height: 100%` (confirm for body text).
- **Letter Spacing:** `--framer-letter-spacing: 0.05em`.
- **Text Transform:** `capitalize` for some elements.

### 7.3. Color and Surfaces

- **Primary Background:** `#fefefe`.
- **Text:** Predominantly `#1E1E1E`, with variations for secondary text and accents.
- **Borders:** `#1E1E1E`, `#dedede`.

### 7.4. Spacing and Rhythm

- **Padding:** `3px 8px`, `8px`, `0 30px`, `10px 7px`, `30px 10px`, `10px 0 100px`, `0 10px`.
- **Margin:** `margin-bottom: 2px`, `margin-bottom: 8px`.
- **Gap:** `0`, `5px`, `10px`, `20px`, `50px`, `70px`, `100px`.

### 7.5. Component Styling

- **Buttons:** Inherited border-radius, `box-shadow: 2px 2px 0px rgba(0,0,0,0.4)`, `text-transform: capitalize`.
- **Cards:** `border: 1px solid #1E1E1E`, `box-shadow: 2px 2px 0px rgba(0,0,0,0.4)`,
