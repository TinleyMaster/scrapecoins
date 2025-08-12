#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫模块包
"""

from .base_scraper import BaseScraper
from .coingecko import CoinGeckoScraper

__all__ = ['BaseScraper', 'CoinGeckoScraper']