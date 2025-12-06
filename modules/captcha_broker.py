"""Pluggable captcha solving interface with multiple provider support."""

import os
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from utils.logging_config import get_logger

logger = get_logger(__name__)


class CaptchaSolver(ABC):
    """Abstract base class for captcha solvers."""
    
    @abstractmethod
    def solve(
        self,
        site_url: str,
        site_key: str,
        captcha_type: str = "recaptcha_v2",
        **kwargs
    ) -> Optional[str]:
        """Solve a captcha challenge.
        
        Args:
            site_url: URL where captcha is located
            site_key: Site key for the captcha
            captcha_type: Type of captcha (recaptcha_v2, recaptcha_v3, hcaptcha, etc.)
            **kwargs: Additional solver-specific parameters
            
        Returns:
            Solved captcha token or None if failed
        """
        pass
    
    @abstractmethod
    def get_balance(self) -> Optional[float]:
        """Get account balance.
        
        Returns:
            Account balance or None if unavailable
        """
        pass


class TwoCaptchaSolver(CaptchaSolver):
    """2Captcha service solver."""
    
    def __init__(self, api_key: str):
        """Initialize 2Captcha solver.
        
        Args:
            api_key: 2Captcha API key
        """
        self.api_key = api_key
        try:
            from twocaptcha import TwoCaptcha
            self.solver = TwoCaptcha(api_key)
        except ImportError:
            logger.error(
                "2captcha-python not installed. Install with: pip install 2captcha-python"
            )
            self.solver = None
    
    def solve(
        self,
        site_url: str,
        site_key: str,
        captcha_type: str = "recaptcha_v2",
        **kwargs
    ) -> Optional[str]:
        """Solve captcha using 2Captcha."""
        if not self.solver:
            return None
        
        try:
            logger.info(
                "captcha_solve_started",
                provider="2captcha",
                site_url=site_url,
                captcha_type=captcha_type
            )
            
            start_time = time.time()
            
            if captcha_type == "recaptcha_v2":
                result = self.solver.recaptcha(
                    sitekey=site_key,
                    url=site_url
                )
            elif captcha_type == "recaptcha_v3":
                result = self.solver.recaptcha(
                    sitekey=site_key,
                    url=site_url,
                    version='v3',
                    action=kwargs.get('action', 'submit')
                )
            elif captcha_type == "hcaptcha":
                result = self.solver.hcaptcha(
                    sitekey=site_key,
                    url=site_url
                )
            else:
                logger.warning(f"Unsupported captcha type: {captcha_type}")
                return None
            
            duration = time.time() - start_time
            
            logger.info(
                "captcha_solved",
                provider="2captcha",
                captcha_type=captcha_type,
                duration=duration
            )
            
            return result['code']
            
        except Exception as e:
            logger.error(
                "captcha_solve_failed",
                provider="2captcha",
                error=str(e)
            )
            return None
    
    def get_balance(self) -> Optional[float]:
        """Get 2Captcha account balance."""
        if not self.solver:
            return None
        
        try:
            balance = self.solver.balance()
            return float(balance)
        except Exception as e:
            logger.error("Failed to get 2captcha balance", error=str(e))
            return None


class AntiCaptchaSolver(CaptchaSolver):
    """AntiCaptcha service solver."""
    
    def __init__(self, api_key: str):
        """Initialize AntiCaptcha solver.
        
        Args:
            api_key: AntiCaptcha API key
        """
        self.api_key = api_key
        try:
            from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
            from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless
            self.recaptcha_solver = recaptchaV2Proxyless()
            self.recaptcha_solver.set_key(api_key)
            self.hcaptcha_solver = hCaptchaProxyless()
            self.hcaptcha_solver.set_key(api_key)
        except ImportError:
            logger.error(
                "anticaptchaofficial not installed. Install with: pip install anticaptchaofficial"
            )
            self.recaptcha_solver = None
            self.hcaptcha_solver = None
    
    def solve(
        self,
        site_url: str,
        site_key: str,
        captcha_type: str = "recaptcha_v2",
        **kwargs
    ) -> Optional[str]:
        """Solve captcha using AntiCaptcha."""
        if not self.recaptcha_solver:
            return None
        
        try:
            logger.info(
                "captcha_solve_started",
                provider="anticaptcha",
                site_url=site_url,
                captcha_type=captcha_type
            )
            
            start_time = time.time()
            
            if captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                self.recaptcha_solver.set_website_url(site_url)
                self.recaptcha_solver.set_website_key(site_key)
                result = self.recaptcha_solver.solve_and_return_solution()
            elif captcha_type == "hcaptcha":
                self.hcaptcha_solver.set_website_url(site_url)
                self.hcaptcha_solver.set_website_key(site_key)
                result = self.hcaptcha_solver.solve_and_return_solution()
            else:
                logger.warning(f"Unsupported captcha type: {captcha_type}")
                return None
            
            duration = time.time() - start_time
            
            if result:
                logger.info(
                    "captcha_solved",
                    provider="anticaptcha",
                    captcha_type=captcha_type,
                    duration=duration
                )
                return result
            else:
                logger.warning("AntiCaptcha returned no solution")
                return None
            
        except Exception as e:
            logger.error(
                "captcha_solve_failed",
                provider="anticaptcha",
                error=str(e)
            )
            return None
    
    def get_balance(self) -> Optional[float]:
        """Get AntiCaptcha account balance."""
        if not self.recaptcha_solver:
            return None
        
        try:
            balance = self.recaptcha_solver.get_balance()
            return float(balance) if balance else None
        except Exception as e:
            logger.error("Failed to get anticaptcha balance", error=str(e))
            return None


class ManualCaptchaSolver(CaptchaSolver):
    """Manual captcha solving (queue for human intervention)."""
    
    def __init__(self):
        """Initialize manual solver."""
        self.pending_captchas = []
    
    def solve(
        self,
        site_url: str,
        site_key: str,
        captcha_type: str = "recaptcha_v2",
        **kwargs
    ) -> Optional[str]:
        """Queue captcha for manual solving.
        
        Returns None immediately. User must solve manually.
        """
        captcha_id = f"{site_url}:{site_key}:{time.time()}"
        
        self.pending_captchas.append({
            'id': captcha_id,
            'site_url': site_url,
            'site_key': site_key,
            'captcha_type': captcha_type,
            'timestamp': time.time()
        })
        
        logger.warning(
            "captcha_queued_for_manual_solving",
            captcha_id=captcha_id,
            site_url=site_url,
            captcha_type=captcha_type
        )
        
        # In a real implementation, this would wait for user input
        # For now, return None to indicate manual intervention needed
        return None
    
    def get_balance(self) -> Optional[float]:
        """Manual solver has no balance."""
        return None
    
    def get_pending(self) -> list:
        """Get list of pending captchas."""
        return self.pending_captchas


class CaptchaBroker:
    """Broker for managing multiple captcha solving providers."""
    
    def __init__(
        self,
        provider: str = None,
        api_key: str = None
    ):
        """Initialize captcha broker.
        
        Args:
            provider: Solver provider (2captcha, anticaptcha, manual)
            api_key: API key for the solver
        """
        self.provider = provider or os.getenv("SOLVER_PROVIDER", "manual")
        api_key = api_key or os.getenv("SOLVER_API_KEY", "")
        
        # Fallback to specific provider keys
        if not api_key:
            if self.provider == "2captcha":
                api_key = os.getenv("TWOCAPTCHA_API_KEY", "")
            elif self.provider == "anticaptcha":
                api_key = os.getenv("ANTICAPTCHA_API_KEY", "")
        
        # Initialize solver
        self.solver: Optional[CaptchaSolver] = None
        
        if self.provider == "2captcha" and api_key:
            self.solver = TwoCaptchaSolver(api_key)
            logger.info("Initialized 2Captcha solver")
        elif self.provider == "anticaptcha" and api_key:
            self.solver = AntiCaptchaSolver(api_key)
            logger.info("Initialized AntiCaptcha solver")
        else:
            self.solver = ManualCaptchaSolver()
            logger.warning("Using manual captcha solver (no API key provided)")
    
    def solve_captcha(
        self,
        site_url: str,
        site_key: str,
        captcha_type: str = "recaptcha_v2",
        **kwargs
    ) -> Optional[str]:
        """Solve a captcha using configured solver.
        
        Args:
            site_url: URL where captcha is located
            site_key: Site key for the captcha
            captcha_type: Type of captcha
            **kwargs: Additional parameters
            
        Returns:
            Solved captcha token or None
        """
        if not self.solver:
            logger.error("No captcha solver configured")
            return None
        
        return self.solver.solve(site_url, site_key, captcha_type, **kwargs)
    
    def get_balance(self) -> Optional[float]:
        """Get solver account balance."""
        if not self.solver:
            return None
        return self.solver.get_balance()
    
    def check_availability(self) -> bool:
        """Check if solver is available and configured."""
        if isinstance(self.solver, ManualCaptchaSolver):
            return False  # Manual solver doesn't auto-solve
        return self.solver is not None
