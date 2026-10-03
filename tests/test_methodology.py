import sys
import unittest
from pathlib import Path
import importlib.util
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import holm, bootstrap_paired, interval
spec=importlib.util.spec_from_file_location('simulation',Path(__file__).resolve().parents[1]/'scripts/01_simulation.py')
sim=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
_pspec=importlib.util.spec_from_file_location('power',Path(__file__).resolve().parents[1]/'scripts/07_power_analysis.py')
power=importlib.util.module_from_spec(_pspec)
_pspec.loader.exec_module(power)
_espec=importlib.util.spec_from_file_location('equivalence',Path(__file__).resolve().parents[1]/'scripts/12_equivalence_power.py')
equivalence=importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(equivalence)

def z_net(a,b,delta):
    """Equation (2): net-response absence."""
    return np.abs(np.asarray(a)+np.asarray(b))<=delta

def z_component(a,b,delta):
    """Equation (3): component-effect absence."""
    return np.maximum(np.abs(a),np.abs(b))<=delta

class StatisticalTests(unittest.TestCase):
    def test_holm_family(self):
        np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])

    def test_paired_known_difference_and_ratio(self):
        d,r=bootstrap_paired(np.full(30,2.),np.ones(30),500,np.random.default_rng(3),block=10)
        np.testing.assert_allclose(d,1)
        np.testing.assert_allclose(r,.5)

    def test_pairing_identical_losses(self):
        x=np.arange(1.,31.)
        d,r=bootstrap_paired(x,x,500,np.random.default_rng(5),block=7)
        np.testing.assert_allclose(d,0)
        np.testing.assert_allclose(r,0)

    def test_zero_baseline_ratio_undefined(self):
        _,r=bootstrap_paired(np.zeros(20),np.ones(20),20,np.random.default_rng(1))
        self.assertTrue(np.isnan(r).all())
        self.assertEqual(interval(r),[None,None])

class ScientificTests(unittest.TestCase):
    def test_observational_equivalence(self):
        result=sim.exact_equivalence()
        self.assertTrue(result['observed_outcomes_identical'])
        self.assertGreater(result['component_active_world1'],.5)
        self.assertEqual(result['component_active_world0'],0)

    def test_population_scale_not_fitted_to_test(self):
        a=sim.generate(23,'strong_signal',100,20)
        b=sim.generate(23,'strong_signal',100,2000)
        np.testing.assert_array_equal(a['x'],b['x'])
        np.testing.assert_array_equal(a['theta'],b['theta'])

    def test_absence_estimands_are_distinct(self):
        f={'retain':np.ones(3,bool),'probabilities':np.tile([0,1,0],(3,1)),
           'confidence':np.ones(3),'hard':np.ones(3,int)}
        result=sim.absence_diagnostics(f,np.zeros(3),np.ones(3),.35)
        self.assertEqual(result['weighted_net_absence_error'],0)
        self.assertEqual(result['weighted_component_absence_error'],1)

    def test_undefined_absence_mass_not_reported_as_zero(self):
        f={'retain':np.zeros(3,bool),'probabilities':np.tile([0,1,0],(3,1)),
           'confidence':np.ones(3),'hard':np.ones(3,int)}
        result=sim.absence_diagnostics(f,np.zeros(3),np.ones(3),.35)
        self.assertTrue(np.isnan(result['weighted_component_absence_error']))

class PowerTests(unittest.TestCase):
    """The minimum detectable effect claims in the manuscript rest on these."""

    def test_mde_matches_closed_form(self):
        # (1.959964 + 0.841621) * sigma at alpha=0.05, power=0.80
        self.assertAlmostEqual(power.mde(1.0,.80),2.801586,places=5)
        self.assertAlmostEqual(power.mde(0.5,.80),1.400793,places=5)

    def test_power_at_mde_returns_target(self):
        for target in (.80,.90):
            for sigma in (.001,.03,1.7):
                self.assertAlmostEqual(power.power_at(power.mde(sigma,target),sigma),
                                       target,places=4)

    def test_power_is_monotone_and_bounded(self):
        values=[power.power_at(e,.03) for e in np.linspace(0,.2,40)]
        self.assertTrue(all(b>=a-1e-12 for a,b in zip(values,values[1:])))
        self.assertAlmostEqual(values[0],.05,places=6)
        self.assertLessEqual(max(values),1.0)

    def test_date_matrix_rejects_unmatched_methods(self):
        import pandas as pd
        frame=pd.DataFrame({'method':['A','A','B'],'Date':['d1','d2','d1'],'loss':[1.,2.,3.]})
        with self.assertRaises(ValueError):
            power.date_loss_matrix(frame,'loss')

class EquivalencePowerTests(unittest.TestCase):
    """Equivalence (TOST) power is a different quantity from difference-test power."""

    def test_zero_when_interval_cannot_fit_inside_margin(self):
        # z_{0.95}*0.0302 = 0.0497 > 0.02: the fresh-pilot situation.
        self.assertEqual(equivalence.equivalence_power(.02,.0302,.05),0.0)
        self.assertEqual(equivalence.equivalence_power(.02,.0091,.0125),0.0)

    def test_closed_form_at_zero_effect(self):
        from scipy import stats
        for se in (.001,.0045,.008):
            expected=max(0.,2*stats.norm.cdf(.02/se-stats.norm.ppf(.95))-1)
            self.assertAlmostEqual(equivalence.equivalence_power(.02,se,.05),expected,places=10)

    def test_size_is_controlled_at_the_margin(self):
        for se in (.002,.005,.009):
            for alpha in (.05,.0125):
                self.assertLessEqual(equivalence.equivalence_power(.02,se,alpha,theta=.02),alpha+1e-12)

    def test_margin_round_trip_and_monotonicity(self):
        for se in (.0003,.0045,.03):
            for alpha in (.05,.0125):
                margin=equivalence.equivalence_margin(se,alpha,.80)
                self.assertAlmostEqual(equivalence.equivalence_power(margin,se,alpha),.80,places=6)
        values=[equivalence.equivalence_power(m,.005,.0125) for m in np.linspace(0,.05,60)]
        self.assertTrue(all(b>=a-1e-12 for a,b in zip(values,values[1:])))

    def test_difference_power_does_not_imply_equivalence_power(self):
        # High power to detect a 2% difference coexists with zero power to certify +/-2% equivalence.
        se=.0091
        self.assertGreater(equivalence.difference_power(.03,se),.85)
        self.assertEqual(equivalence.equivalence_power(.02,se,.0125),0.0)

    def test_family_level_matches_published_family_interval(self):
        # The family interval in 03_inference_and_report.py is interval(rel, .1/4).
        from scipy import stats
        draws=np.random.default_rng(4).normal(size=2_000_000)
        low,high=interval(draws,.1/4)
        z=stats.norm.ppf(1-equivalence.FAMILY_ALPHA)
        self.assertAlmostEqual(high,z,places=2)
        self.assertAlmostEqual(low,-z,places=2)
        self.assertAlmostEqual(equivalence.FAMILY_ALPHA,.0125)

    def test_decision_reads_intervals(self):
        d=equivalence.decision
        self.assertEqual(d(.0004,-.2355,-.1004,.02),'RDFL_WORSE_BEYOND_MARGIN')
        self.assertEqual(d(.0004,.0134,.0279,.02),'DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN')
        self.assertEqual(d(.58,-.0132,.0074,.02),'EQUIVALENT_WITHIN_MARGIN')
        self.assertEqual(d(.13,.0013,.0409,.02),'INCONCLUSIVE')

class AbsenceEstimandTests(unittest.TestCase):
    """The relationship between equations (2) and (3) stated after equation (3)."""

    def test_subthreshold_components_without_cancellation(self):
        # Reviewer counterexample: no cancellation, yet the two indicators disagree.
        self.assertFalse(z_net(.2,.2,.35))
        self.assertTrue(z_component(.2,.2,.35))

    def test_cancellation_is_required_for_false_absence(self):
        rng=np.random.default_rng(11)
        a,b=rng.normal(size=200000),rng.normal(size=200000)
        delta=.35
        false_absence=z_net(a,b,delta)&~z_component(a,b,delta)
        self.assertTrue(false_absence.any())
        self.assertTrue((a[false_absence]*b[false_absence]<0).all())
        same_sign=a*b>=0
        self.assertTrue((z_net(a,b,delta)[same_sign]<=z_component(a,b,delta)[same_sign]).all())

    def test_single_component_and_triangle_bound(self):
        rng=np.random.default_rng(12)
        a,b=rng.normal(size=100000),rng.normal(size=100000)
        for delta in (.2,.35,.5):
            np.testing.assert_array_equal(z_net(a,0*a,delta),z_component(a,0*a,delta))
            self.assertTrue((z_component(a,b,delta)<=z_net(a,b,2*delta)).all())

    def test_net_only_bounds_are_sharp(self):
        # Proposition 1: |A+B| > 2 delta forces an active component; |A+B| <= 2 delta admits both states.
        rng=np.random.default_rng(13)
        a,b=rng.normal(size=100000),rng.normal(size=100000)
        s=a+b
        self.assertTrue((np.maximum(np.abs(a),np.abs(b))>=np.abs(s)/2-1e-12).all())
        delta=.35
        for value in rng.uniform(-2*delta,2*delta,size=200):
            self.assertTrue(z_component(value/2,value/2,delta))           # split into two halves
            self.assertFalse(z_component(value+5.,-5.,delta))             # split with a large offset
            self.assertTrue(z_net(value/2,value/2,2*delta))

    def test_gross_activity_identifies_cancellation(self):
        # Proposition 2: with G = |A| + |B|, opposite signs give max = (G + |S|)/2 exactly;
        # the only remaining ambiguity is the same-sign case, where G = |S| and max lies in [G/2, G].
        rng=np.random.default_rng(14)
        a,b=rng.normal(size=100000),rng.normal(size=100000)
        g,s,m=np.abs(a)+np.abs(b),np.abs(a+b),np.maximum(np.abs(a),np.abs(b))
        opposite=a*b<0
        np.testing.assert_allclose(m[opposite],(g[opposite]+s[opposite])/2,atol=1e-12)
        np.testing.assert_allclose(g[~opposite],s[~opposite],atol=1e-12)
        self.assertTrue(((m[~opposite]>=g[~opposite]/2-1e-12)&(m[~opposite]<=g[~opposite]+1e-12)).all())

    def test_observable_bound_inequality(self):
        # Corollary: with Y = S + eps, 1{|S|>2d} >= 1{|Y|>2d+k} - 1{|eps|>k} for every k >= 0.
        rng=np.random.default_rng(15)
        s,eps=rng.normal(size=100000),rng.normal(scale=.7,size=100000)
        y=s+eps
        for k in (0.,.3,1.,2.5):
            lhs=(np.abs(s)>.7).astype(int)
            rhs=(np.abs(y)>.7+k).astype(int)-(np.abs(eps)>k).astype(int)
            self.assertTrue((lhs>=rhs).all())

    def test_observable_bound_is_zero_when_labels_select_small_responses(self):
        spec=importlib.util.spec_from_file_location('observable',Path(__file__).resolve().parents[1]/'scripts/23_observable_bounds.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        rng=np.random.default_rng(16)
        y=rng.normal(scale=.2,size=5000)                   # low-response selection: small |Y|
        bound,_=module.observable_lower_bound(np.ones(5000),y,.7)
        self.assertEqual(bound,0.0)
        y_large=np.full(5000,5.)                           # every |Y| far above 2 delta
        bound,_=module.observable_lower_bound(np.ones(5000),y_large,.7)
        self.assertGreater(bound,.99)

    def test_simulation_diagnostic_uses_the_same_definitions(self):
        # A=B=0.2 retained as low response: component absent, net response present.
        f={'retain':np.ones(1,bool),'probabilities':np.array([[0.,1.,0.]]),
           'confidence':np.ones(1),'hard':np.ones(1,int)}
        result=sim.absence_diagnostics(f,np.array([.4]),np.array([.2]),.35)
        self.assertEqual(result['weighted_component_absence_error'],0)
        self.assertEqual(result['weighted_net_absence_error'],1)

class SimulationExtensionTests(unittest.TestCase):
    """18_simulation_extensions.py must mirror 01_simulation.py at lambda = 0."""

    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('extensions',Path(__file__).resolve().parents[1]/'scripts/18_simulation_extensions.py')
        cls.ext=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ext)

    def test_lambda_zero_reproduces_original_generator(self):
        mine=self.ext.generate(21001,300,50,20)
        theirs=sim.generate(21001,'cancellation_085',300,50,20)
        for key in ['x','y','theta','volume','component']:
            np.testing.assert_array_equal(mine[key],theirs[key])

    def test_lambda_one_volume_tracks_gross_activity(self):
        d0=self.ext.generate(5,4000,10,20,volume_lambda=0.)
        d1=self.ext.generate(5,4000,10,20,volume_lambda=1.)
        gross=np.abs(d1['a'])+np.abs(d1['b'])
        self.assertGreater(np.corrcoef(d1['volume'],gross)[0,1],np.corrcoef(d0['volume'],gross)[0,1])

    def test_nonlinear_scale_is_population_not_sample(self):
        a=self.ext.generate(8,100,20,20,cancel=0.,nonlinear=True)
        b=self.ext.generate(8,100,2000,20,cancel=0.,nonlinear=True)
        np.testing.assert_array_equal(a['theta'],b['theta'])

if __name__=='__main__':
    unittest.main()
