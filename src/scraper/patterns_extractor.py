# -*- coding: utf-8 -*-
"""
scraper/patterns_extractor.py

Handles extraction of data from 'altfins-trading-pattern-component' cards,
which are used in both 'Chart Patterns' and 'Market Highlights' pages.
Uses Playwright's shadow DOM support.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel
from src.logger import get_logger

log = get_logger(__name__)

class PatternExtraction(BaseModel):
    symbol: str
    coin: str
    pattern_name: str
    interval: str = "N/A"
    status: str = "N/A"
    raw_text: str
    image_url: str
    is_locked: bool = False
    signal: str = "N/A"
    trend: str = "N/A"
    profit_potential: str = "N/A"
    price: str = "N/A"
    price_change: str = "N/A"

def extract_patterns(page, source_type: str = "CHART_PATTERN") -> List[PatternExtraction]:
    """
    Finds trading pattern elements and extracts data using exact DOM targeting.
    """
    log.info("Extracting trading patterns from %s...", source_type)
    
    # Scroll down to load all cards
    try:
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(2000)
        
        # Robust wait: ensure components are attached and have shadow roots with content
        page.evaluate('''() => {
            return new Promise(resolve => {
                let attempts = 0;
                const check = setInterval(() => {
                    const comps = document.querySelectorAll('altfins-trading-pattern-component');
                    let readyCount = 0;
                    comps.forEach(c => {
                        // A card is "ready" if it has a shadow root and either a description or a detail-row
                        if (c.shadowRoot) {
                            const hasContent = c.shadowRoot.querySelector('.detail-row-label') || 
                                               c.shadowRoot.querySelector('.description') ||
                                               c.shadowRoot.querySelector('.upgrade-unlock-container');
                            if (hasContent) readyCount++;
                        }
                    });
                    // Wait for at least 2 cards to be "ready" or timeout
                    if (readyCount >= 2 || attempts > 30) {
                        clearInterval(check);
                        resolve();
                    }
                    attempts++;
                }, 200);
            });
        }''')
    except Exception as e:
        log.warning("Wait loop interrupted: %s", e)

    # Extraction script with precise targeting
    extraction_script = """(sourceType) => {
        const results = [];
        
        // 1. Capture Global Interval
        let globalInterval = "N/A";
        const menuButtons = Array.from(document.querySelectorAll('vaadin-menu-bar-button, vaadin-menu-bar-item'));
        const activeInterval = menuButtons.find(btn => {
            const txt = btn.innerText.trim().toLowerCase();
            const isValidText = ["15m", "1h", "4h", "1d", "1w"].includes(txt);
            const isActive = btn.hasAttribute('highlight') || btn.hasAttribute('selected') || btn.getAttribute('aria-selected') === 'true';
            return isValidText && isActive;
        });
        
        if (activeInterval) {
            globalInterval = activeInterval.innerText.trim();
        } else {
            const fallback = menuButtons.find(btn => ["15m", "1h", "4h", "1d", "1w"].includes(btn.innerText.trim().toLowerCase()));
            if (fallback) globalInterval = fallback.innerText.trim();
        }

        // 2. Select Components based on source type
        let targetComponents = [];
        
        if (sourceType === "MARKET_HIGHLIGHT") {
            // Take ALL altfins-trading-pattern-component from the FIRST vaadin-board-row only
            const firstRow = document.querySelector('vaadin-board-row');
            if (firstRow) {
                targetComponents = Array.from(firstRow.querySelectorAll('altfins-trading-pattern-component'));
            }
        } else {
            // CHART_PATTERN: All components on the page
            targetComponents = Array.from(document.querySelectorAll('altfins-trading-pattern-component'));
        }

        // 3. Extract Data
        targetComponents.forEach(component => {
            const shadow = component.shadowRoot;
            if (!shadow) return;

            // Check for Lock
            const isLockedLight = component.querySelector('altfins-chart-pattern-locked-img') !== null;
            const isLockedShadow = shadow.querySelector('altfins-chart-pattern-locked-img') !== null || 
                                   shadow.querySelector('.upgrade-unlock-container') !== null ||
                                   shadow.textContent.includes('Upgrade to unlock');
            
            const isLocked = isLockedLight || isLockedShadow;

            // Extract Header (Light DOM child but with its own shadow root)
            const widgetHeader = component.querySelector('widget-header');
            let symbol = "";
            let coin = "";
            let price = "N/A";
            let priceChange = "N/A";

            if (widgetHeader && widgetHeader.shadowRoot) {
                const primary = widgetHeader.shadowRoot.querySelector('#primary');
                const secondary = widgetHeader.shadowRoot.querySelector('#secondary');
                symbol = primary ? primary.innerText.trim() : "";
                coin = secondary ? secondary.innerText.trim() : "";
                
                // Extract Price and Change from Header
                // Typically inside .badge-container or similar
                const headerText = widgetHeader.shadowRoot.textContent || "";
                const priceMatch = headerText.match(/\$\s*([0-9.,]+)/);
                const changeMatch = headerText.match(/([+-]?\s*[0-9.,]+%)/);
                
                if (priceMatch) price = priceMatch[0].trim();
                if (changeMatch) priceChange = changeMatch[0].trim();
            }

            // Extract Details
            const getVal = (label) => {
                const rows = Array.from(shadow.querySelectorAll('.detail-row-label'));
                const target = rows.find(r => r.innerText.includes(label));
                return target ? target.parentElement.innerText.replace(label, "").trim() : "N/A";
            };

            const patternName = getVal('Pattern:');
            const signal = getVal('Signal:');
            const trend = getVal('Trend:');
            
            // Per-card interval if global is missing
            let cardInterval = getVal('Interval:');
            if (cardInterval === "N/A") cardInterval = globalInterval;

            // Profit Potential - more robust extraction
            const profitEl = shadow.querySelector('.profit-potential');
            let profitPotential = "N/A";
            if (profitEl) {
                const pText = profitEl.innerText;
                const pMatch = pText.match(/[+-]?\s*[0-9.,]+%/);
                profitPotential = pMatch ? pMatch[0].trim() : "N/A";
            }

            const descEl = shadow.querySelector('span.description') || shadow.querySelector('[part="description"]');
            const rawText = descEl ? descEl.innerText.trim() : "N/A";
            const status = rawText.toLowerCase().includes("forming") ? "Forming" : "Completed";

            const img = shadow.querySelector('img.chart') || shadow.querySelector('.img-container img') || shadow.querySelector('img:not([src*="fullscreen"])');
            const imgSrc = img ? img.getAttribute('src') : "";

            results.push({
                symbol,
                coin,
                pattern_name: patternName,
                signal,
                trend,
                profit_potential: profitPotential,
                status,
                interval: cardInterval,
                raw_text: rawText,
                img_src: imgSrc,
                is_locked: isLocked,
                price: price,
                price_change: priceChange
            });
        });

        return results;
    }"""

    try:
        data_list = page.evaluate(extraction_script, source_type)
    except Exception as e:
        log.error("Failed to evaluate extraction script: %s", e)
        return []

    results = []
    base_url = "https://altfins.com"

    for i, data in enumerate(data_list):
        symbol = data['symbol']
        if not symbol: continue
        
        # Skip locked cards if they have no pattern data
        if data['is_locked'] and data['pattern_name'] == "N/A":
            log.info("Skipping locked pattern card for %s", symbol)
            continue
            
        coin = data['coin'] or symbol
        log.info("Processing card %d: %s (%s) - Locked: %s", i + 1, coin, symbol, data['is_locked'])
        
        image_url = data['img_src']
        if image_url:
            if not image_url.startswith("http"):
                image_url = f"{base_url}{image_url if image_url.startswith('/') else '/' + image_url}"
        
        results.append(PatternExtraction(
            symbol=symbol,
            coin=coin,
            pattern_name=data['pattern_name'],
            interval=data['interval'],
            status=data['status'],
            raw_text=data['raw_text'],
            image_url=image_url or "",
            is_locked=data['is_locked'],
            signal=data['signal'],
            trend=data['trend'],
            profit_potential=data['profit_potential'],
            price=data['price'],
            price_change=data['price_change']
        ))
            
    log.info("Extracted %d valid patterns.", len(results))
    return results

