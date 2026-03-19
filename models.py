import pandas as pd
import datetime

class ExcelBitcoinModel:
    def __init__(self, historical_df, current_price, aths):
        self.df = historical_df.sort_index()
        self.current_price = current_price
        self.aths = aths
        self.current_date = datetime.date.today()
        
    def detect_market_phase(self, current_ath_price):
        """
        Classify roughly: 
        Early Bear -> Initial drop
        Capitulation -> Drop > 60%
        Rebound -> Recovery
        Distribution -> near ATH
        """
        drawdown = ((self.current_price / current_ath_price) - 1.0) * 100
        days_from_ath = (self.current_date - self.aths['current']['date']).days
        
        if drawdown > -15:
            if days_from_ath < 300:
                return "Distribution / Bull"
            else:
                return "Re-Accumulation / Pre-Bull"
        elif drawdown < -60:
            return "Capitulation / Deep Bear"
        elif drawdown < -15 and days_from_ath < 400:
            return "Early Bear"
        else:
            return "Rebound / Recovery"

    def get_historical_smoothed_price(self, ref_cycle, days_offset):
        ref_ath_date = self.aths[ref_cycle]['date']
        equivalent_date = ref_ath_date + datetime.timedelta(days=days_offset)
        
        max_date = self.df.index.max()
        if equivalent_date > max_date: equivalent_date = max_date
            
        start = equivalent_date - datetime.timedelta(days=5)
        end = equivalent_date + datetime.timedelta(days=5)
        window = [p for d, p in self.df['price'].items() if start <= d <= end]
        
        if window: return sum(window) / len(window)
        
        fallback_window = [p for d, p in self.df['price'].items() if (equivalent_date - datetime.timedelta(days=15)) <= d <= equivalent_date]
        if fallback_window: return sum(fallback_window) / len(fallback_window)
        return self.aths[ref_cycle]['price']

    def calculate_power_law(self, target_date):
        genesis_date = datetime.date(2009, 1, 3)
        t = (target_date - genesis_date).days
        if t <= 0: return 0
        return 1.35e-17 * (t ** 5.87)

    def calculate_halving_model(self, target_date):
        halving_2024 = datetime.date(2024, 4, 19)
        halving_2020 = datetime.date(2020, 5, 11)
        days_since_2024_halving = max(0, (target_date - halving_2024).days)
        equivalent_2020_date = halving_2020 + datetime.timedelta(days=days_since_2024_halving)
        
        max_date = self.df.index.max()
        if equivalent_2020_date > max_date: equivalent_2020_date = max_date
            
        start = equivalent_2020_date - datetime.timedelta(days=5)
        end = equivalent_2020_date + datetime.timedelta(days=5)
        window = [p for d, p in self.df['price'].items() if start <= d <= end]
        hist_target = sum(window)/len(window) if window else 69000
        
        start_h = halving_2020 - datetime.timedelta(days=5)
        end_h = halving_2020 + datetime.timedelta(days=5)
        window_h = [p for d, p in self.df['price'].items() if start_h <= d <= end_h]
        hist_halving = sum(window_h)/len(window_h) if window_h else 8600
        
        growth = hist_target / hist_halving
        return 64000 * growth
        
    def calculate_regime_model(self, target_date):
        pl_price = self.calculate_power_law(target_date)
        days_to_target = (target_date - self.current_date).days
        if days_to_target <= 0: return self.current_price
        
        weight_current = max(0.0, 1.0 - (days_to_target / 365.0))
        weight_pl = 1.0 - weight_current
        return (self.current_price * weight_current) + (pl_price * weight_pl)

    def predict(self, target_date, reference_cycle='Auto'):
        current_ath_date = self.aths['current']['date']
        current_ath_price = self.aths['current']['price']
        
        days_today = (self.current_date - current_ath_date).days
        days_target = max(0, (target_date - current_ath_date).days)
        
        def get_multiplier(ref_cycle):
            price_today = self.get_historical_smoothed_price(ref_cycle, days_today)
            price_target = self.get_historical_smoothed_price(ref_cycle, days_target)
            return price_target / price_today if price_today > 0 else 1.0
            
        if reference_cycle == 'Auto':
            mult_2021 = get_multiplier('2021')
            mult_2017 = get_multiplier('2017')
            cycle_mult = (0.90 * mult_2021) + (0.10 * mult_2017)
            cycle_label = "Auto Blend"
        else:
            cycle_mult = get_multiplier(reference_cycle)
            cycle_label = f"{reference_cycle} Cycle"
            
        pl_today = self.calculate_power_law(self.current_date)
        pl_target = self.calculate_power_law(target_date)
        pl_mult = pl_target / pl_today if pl_today > 0 else 1.0
        
        halv_today = self.calculate_halving_model(self.current_date)
        halv_target = self.calculate_halving_model(target_date)
        halv_mult = halv_target / halv_today if halv_today > 0 else 1.0
        
        # Regime Simulation
        days_from_now = (target_date - self.current_date).days
        if days_from_now <= 0:
            regime_mult = 1.0
        else:
            weight_current = max(0.0, 1.0 - (days_from_now / 365.0))
            weight_pl = 1.0 - weight_current
            regime_target_abs = (self.current_price * weight_current) + (pl_target * weight_pl)
            regime_mult = regime_target_abs / self.current_price
        
        # Multi-Factor Synthesis is ALWAYS used for robustness
        mult_final = (0.50 * cycle_mult) + (0.20 * pl_mult) + (0.15 * halv_mult) + (0.15 * regime_mult)
        
        predicted_price = self.current_price * mult_final
        ref_year_label = f"Hybrid Model ({cycle_label})"
        final_ratio = mult_final
        
        bear = predicted_price * 0.85
        bull = predicted_price * 1.15
        
        drawdown = ((self.current_price / current_ath_price) - 1.0) * 100
        phase = self.detect_market_phase(current_ath_price)
        
        return {
            "estimated_price": predicted_price,
            "bear": bear,
            "base": predicted_price,
            "bull": bull,
            "ratio": final_ratio,
            "reference_cycle": ref_year_label,
            "market_phase": phase,
            "drawdown": drawdown,
            "current_ath_price": current_ath_price,
            "days_target": days_target
        }
