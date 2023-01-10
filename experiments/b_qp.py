import numpy as np
from maple.cart import RegTree
from maple.grad_boost import GradBoost
from maple.control import cart_control, grad_boost_control, random_forest_control
from maple.random_forest import RandomForest
from dboost_py.optim_scs import OptimScs
from dboost_py.control import scs_control
from dboost_py.spot import SPOTree, QSPOTree
from dboost_py.dboost import DboostSPO, DboostQSPO
from dboost_py.loss import loss_qspo
from experiments.utils import generate_problem_data
import matplotlib.pyplot as plt

# --- problem setup:
n_obs = 1000
n_x = 5
pct_true = 0.5
poly_degree=[1,2,3]
intercept=False
intercept_mean=-0
noise_multiplier_tau=0

# --- qp problem:
n_z = 10#25
A = np.ones((1,n_z))
b = np.ones((1, 1))
cone ={"z":1}


# --- experiment:
n_sims = 10
idx_all = np.arange(2*n_obs)
idx_train = np.arange(n_obs)
idx_oos = idx_all[n_obs:]

# --- control:
control = cart_control(fit_type='regression', demean=False, max_depth=0, min_obs=0.05, step_size=0.05)
control_rf = random_forest_control(num_trees=100, obs_fraction=0.50, vars_fraction=0.50, verbose=True)
control_gb = grad_boost_control(num_trees=100, verbose=True, weight_tol=0.01,
                                loss_tol=10 ** -6, alpha_min=0, alpha_max=10)


# --- model_names:
model_names = ['RegTree','SPOT','RandomForest',"SPOTForest",'GradBoost','Dboost']
n_models = len(model_names)
in_sample_cost = np.zeros((n_sims,n_models+1))
out_of_sample_cost = np.zeros((n_sims,n_models+1))


# --- main loop:
for i in range(n_sims):
    print('Simulation = {:d}'.format(i))

    # --- generate data
    data = generate_problem_data(n_x=n_x, n_z=n_z, n_obs=2 * n_obs, pct_true=pct_true,
                                 noise_multiplier_tau=noise_multiplier_tau,
                                 polys=poly_degree, intercept=intercept,
                                 intercept_mean=intercept_mean)

    x = data.get('x')
    cost = data.get('cost')
    x_train = x[idx_train, :]
    cost_train = cost[idx_train, :]
    x_oos = x[idx_oos, :]
    cost_oos = cost[idx_oos, :]

    # --- P:
    L = np.random.uniform(low=-1,high=1,size=(n_z, n_z))
    P_true = np.dot(L.T, L) + 0.01*np.identity(n_z)
    L = np.random.normal(size=(10*n_z, n_z))
    error_train = np.dot(L.T, L)/(10*n_z)
    L = np.random.normal(size=(10 * n_z, n_z))
    error_oos = np.dot(L.T, L) / (10 * n_z)
    P_train = P_true + 0.10 * error_train
    P_oos = P_true + 0.10 * error_oos


    # --- cost star train:
    oracle = OptimScs(A=A, b=b, cone=cone, P=P_true, P_eval=P_true, control=scs_control())
    cost_star_train = loss_qspo(y=cost_train, y_hat=cost_train, oracle=oracle)
    cost_star_oos = loss_qspo(y=cost_oos, y_hat=cost_oos, oracle=oracle)
    in_sample_cost[i,n_models] = cost_star_train
    out_of_sample_cost[i, n_models] = cost_star_oos

    j = 0
    for nm in model_names:
        print(nm)
        oracle = OptimScs(A=A, b=b, cone=cone, P=P_train,P_eval=P_true, control=scs_control())
        if nm == "RegTree":
            model = RegTree(control=control)
        elif nm == "SPOT":
            model = QSPOTree(oracle=oracle, control=control)
        elif nm == "RandomForest":
            weak_learner = RegTree(control=control)
            model = RandomForest(control=control_rf, weak_learner=weak_learner)
        elif nm == "SPOTForest":
            weak_learner = QSPOTree(oracle=oracle, control=control)
            model = RandomForest(control=control_rf, weak_learner=weak_learner)
        elif nm == "GradBoost":
            weak_learner = RegTree(control=control)
            model = GradBoost(weak_learner=weak_learner, control=control_gb)
        elif nm == "Dboost":
            weak_learner = DboostQSPO(oracle=oracle, control=control)
            model = GradBoost(weak_learner=weak_learner, control=control_gb)

        # ---fit
        model.fit(x=x_train,y=cost_train)
        cost_hat_train = model.predict(x=x_train)
        cost_hat_oos = model.predict(x=x_oos)

        # --- cost_hat train and oos:
        result_train = loss_qspo(y=cost_train, y_hat=cost_hat_train, oracle=oracle)
        oracle = OptimScs(A=A, b=b, cone=cone, P=P_oos, P_eval=P_true, control=scs_control())
        result_oos = loss_qspo(y=cost_oos, y_hat=cost_hat_oos, oracle=oracle)

        in_sample_cost[i,j]=result_train
        out_of_sample_cost[i,j]=result_oos
        j = j+1


test = out_of_sample_cost[:,0:6]
for i in range(test.shape[0]):
    test[i,:]=(test[i,:] -out_of_sample_cost[i,6]) /abs(out_of_sample_cost[i,6])

plt.boxplot(test)