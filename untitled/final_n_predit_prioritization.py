import numpy as np
import sqlite3
import sys
from read_model import read_images_binary, read_points3d_binary
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics
import csv
import pickle
from sklearn.cluster import KMeans, MiniBatchKMeans
from fptas import FPTAS
from operator import itemgetter
import random
import matplotlib.pyplot as plt
import time
from sklearn.utils import shuffle
from sklearn.tree import export_graphviz
from sklearn.externals.six import StringIO
from IPython.display import Image
import matplotlib.image as mpimg
from subprocess import call
import pydotplus
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import chi2
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
import warnings
import statsmodels.formula.api as sm
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler

warnings.filterwarnings("ignore")
sys.setrecursionlimit(150000000)
# csv_file_test_image = "/home/earl/Thesis/GreatCourt/test_image.csv"
database_locatiom = "/home/earlfernando/shopfacade/shopfacade.db"
image_bin_location = "/home/earlfernando/shopfacade/images.bin"
csv_file_location_400000 = "/home/earlfernando/shopfacade/training_Data_RandomForest_overall.csv"
images_test_file_location = "/home/earlfernando/shopfacade/dataset_test.txt"
# file_name_random_forest = "/home/earl/Thesis/GreatCourt/test_model_random_forest_10000.sav"
file_name_kmeans = "/home/earlfernando/shopfacade/test_model_kmeans.sav"
feature_length = 128
csv_file_location_kmeans = "/home/earlfernando/shopfacade/train_kmeans.csv"
number_of_clusters = 10000
database_location_overall = "/home/earlfernando/shopfacade/shopfacade.db"
image_bin_location_overall = "/home/earlfernando/shopfacade/images.bin"
point3D_location_overall = "/home/earlfernando/shopfacade/points3D.bin"
# csv_file_location_kmeans_test = "/home/earlfernando/greatCourtTrinity/GreatCourt//test_kmeans_modified.csv"
csv_file_location_kmeans_test = "/home/earlfernando/shopfacade/test_kmeans_modified.csv"
max_cost = 20000


def blob_to_array(blob, dtype, shape=(-1,)):
    IS_PYTHON3 = sys.version_info[0] >= 3
    if IS_PYTHON3:
        return np.fromstring(blob, dtype=dtype).reshape(*shape)
    else:
        return np.frombuffer(blob, dtype=dtype).reshape(*shape)


def check(array_local, x, y):
    return_value = False

    b = np.array(array_local[:, 0] == x)
    list_of_row_indices = np.where(b)
    for i in list_of_row_indices:
        if array_local[i] == [x, y]:
            return_value = True
            break
    return return_value


class image:
    def __init__(self, name, train_test):
        self.name = name
        self.feature_location = []
        self.descriptor = []
        self.poistive_descriptor = []
        self.poistive_descriptor_location = []
        self.negative_descriptor = []
        self.negative_descriptor_location = []
        self.positive_index = []
        self.train_test = train_test

    def add_positve(self, x, y):
        # if not check(self.poistive_descriptor_location,x,y):
        list_of_row_indices = np.where(np.array(self.feature_location[:, 0]) == x)

        b = self.feature_location
        c = np.array(self.feature_location[:, 0]) == x
        f = np.where(c)
        d = b[c]
        t = 0

        for i in list_of_row_indices[0]:
            t += 1

            truth = self.feature_location[i]
            if truth[1] == y:
                self.positive_index.append(i)
                self.poistive_descriptor_location.append([x, y])
                start = i * 128

                end = start + 128
                t = np.arange(start, end)
                descriptor = self.descriptor[t]

                self.poistive_descriptor.append(descriptor)
                break

    def add_negative(self):
        mask = np.ones(np.shape(self.feature_location)[0], dtype=bool)
        mask[self.positive_index] = False
        self.negative_descriptor_location = self.feature_location[mask]
        for number, i in enumerate(mask):
            if i:
                start = number * 128
                end = start + 128
                t = np.arange(start, end)
                descriptor = self.descriptor[t]

                self.negative_descriptor.append(descriptor)


def add_feature_location(database_location, images_test_file_location):
    database = sqlite3.connect(database_location)
    cursor = database.cursor()
    test_images_id = []
    training_images_id = []

    test_images_str = test_images_string(images_test_file_location)
    cursor.execute('''SELECT image_id,name FROM IMAGES ''')

    for row in cursor:
        """image_name = row[1].split('/')
        if image_name[0]=='test':
            test_images_id.append(row[0])"""
        if row[1] in test_images_str:
            test_images_id.append(row[0])
        else:
            training_images_id.append(row[0])
    database.close()
    training_images_id = np.array(training_images_id)
    test_images_id = np.array(test_images_id)
    print(len(test_images_id))

    class_array = []

    database = sqlite3.connect(database_location)
    cursor = database.cursor()
    second_curosr = database.cursor()
    # cursor.execute('''SELECT image_id,data,rows FROM  descriptors''')

    cursor.execute('''SELECT image_id,data,rows FROM descriptors''')
    second_curosr.execute('''SELECT image_id, data, rows FROM keypoints''')
    counter = 0
    for first, row in zip(second_curosr, cursor):
        """if str(row[0])== str(first[0]):

            print(str(row[0]),np.shape(blob_to_array(row[1],dtype=np.uint8)),str(row[2]),blob_to_array(row[1],dtype=np.uint8))
        else:
            return print("Error image_id doesnt match")
        print(blob_to_array(first[1],dtype= np.float32), str(first[2]),np.shape(blob_to_array(first[1],dtype= np.float32)))
        #features_location_local = [blob_to_array(first[1],dtype= np.float32)[::6],blob_to_array(first[1],dtype= np.float32)[1::6]]
        #new_location = np.column_stack((blob_to_array(first[1],dtype= np.float32)[::6],blob_to_array(first[1],dtype= np.float32)[1::6]))"""

        mask_test = test_images_id == row[0]

        mask_train = training_images_id == row[0]

        if len(test_images_id[mask_test]) == 1:
            test_train = 0

        else:
            test_train = 1

        class_array.append(image(str(row[0]), train_test=test_train))

        class_array[counter].feature_location = np.column_stack(
            (blob_to_array(first[1], dtype=np.float32)[::6], blob_to_array(first[1], dtype=np.float32)[1::6]))
        class_array[counter].descriptor = np.array(blob_to_array(row[1], dtype=np.uint8))
        counter += 1

    database.close()
    return class_array


def make_training_data(cameras, image_array):
    for rand, cam in enumerate(cameras):

        for h, k in enumerate(cameras[cam].point3D_ids):

            if k >= 0:
                id = cameras[cam].xys[h]
                image_array[cam - 1].add_positve(id[0], id[1])

        image_array[cam - 1].add_negative()

    postive_samples = []
    negative_samples = []
    for image in image_array:
        if image.train_test == 1:
            for descriptor in image.poistive_descriptor:
                postive_samples.append(descriptor)

            for descriptor in image.negative_descriptor:
                negative_samples.append(descriptor)
    return postive_samples, negative_samples


def make_testing_data(cameras, image_array):
    for rand, cam in enumerate(cameras):

        o = cameras[cam].point3D_ids
        local_image = image_array[cam - 1]
        counter = 0
        for h, k in enumerate(cameras[cam].point3D_ids):
            counter += 1
            if k >= 0:
                id = cameras[cam].xys[h]
                image_array[cam - 1].add_positve(id[0], id[1])
        image_array[cam - 1].add_negative()
        if len(image_array[cam - 1].poistive_descriptor) == 0:
            print('error')

    return image_array


def create_headers(feature_length):
    columns = []
    for i in range(feature_length):
        columns.append(str(i))

    return columns


def handle_data(positive, negative, feature_length, csv_file_location):
    print('data_handling')
    headers = create_headers(feature_length)
    headers.append('label')
    # positive = random.sample(positive, 10000)
    # negative = random.sample(negative, 10000)
    print(np.shape(positive)[0], np.shape(negative)[0])

    positive_label = np.ones((np.shape(positive)[0], 1))
    negative_label = np.zeros((np.shape(negative)[0], 1))
    training_samples = np.vstack((positive, negative))
    training_labels = np.vstack((positive_label, negative_label))
    shuffling_array = np.arange(np.shape(positive)[0] + np.shape(negative)[0])
    np.random.shuffle(shuffling_array)
    print(np.shape(positive)[0] + np.shape(negative)[0])

    # shape_training_labels = np.shape(training_labels[0])
    # samples = np.append(training_samples, training_labels, axis=1)

    with open(csv_file_location, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for i in shuffling_array:
            label = training_labels[i]
            descriptor = training_samples[i]
            k = np.append(descriptor, label)
            # values.append(tuple(k))
            writer.writerow(k)

    # for i in samples:
    # values.append(tuple(i))
    csvfile.close()

    return headers


def handle_data_for_test(positive, negative, feature_length, csv_file_location_kmeans):
    print('data_handling')
    headers = create_headers(feature_length)
    headers.append('label')
    training_samples = np.vstack((positive, negative))

    # shape_training_labels = np.shape(training_labels[0])
    # samples = np.append(training_samples, training_labels, axis=1)
    # samples_kmeans = random.sample(samples,100000)
    with open(csv_file_location_kmeans, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for j, i in enumerate(training_samples):
            # values.append(tuple(k))
            writer.writerow(i)

    # for i in samples:
    # values.append(tuple(i))
    csvfile.close()

    return headers


def handle_data_for_kmeans(positive, negative, feature_length, csv_file_location_kmeans):
    print('data_handling')
    headers = create_headers(feature_length)
    headers.append('label')
    positive = random.sample(positive, 100000)

    # shape_training_labels = np.shape(training_labels[0])
    # samples = np.append(training_samples, training_labels, axis=1)
    # samples_kmeans = random.sample(samples,100000)
    with open(csv_file_location_kmeans, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for j, i in enumerate(positive):
            # values.append(tuple(k))
            writer.writerow(i)

    # for i in samples:
    # values.append(tuple(i))
    csvfile.close()

    return headers


def random_forest(headers, feature_length, csv_file_location, file_name):
    # df = pd.DataFrame.from_records(values, columns=headers)

    df = pd.read_csv(csv_file_location, names=headers)

    print("csv_read")
    X = df[create_headers(feature_length)]
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
    clf = RandomForestClassifier(n_estimators=1000, max_features=None)
    print('training')
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print("Accuracy:", metrics.accuracy_score(y_test, y_pred))
    pickle.dump(clf, open(file_name, 'wb'))


def feature_selection(number):
    csv_file_location_local = "/home/earl/Thesis/shopfacade/training_Data_RandomForest_10000.csv"
    if number == 0:
        selected_columns = create_headers(feature_length)
    if number >= 1:
        chunk = pd.read_csv(csv_file_location_local)
        # X= chunk[create_headers(feature_length)]
        # print(X.shape)
        # y = chunk['label']
        # clf.fit(X, y)
        data = chunk.iloc[:, 0:-1]
        corr = data.corr()
        # sns.heatmap(corr)
        # plt.show()
        columns = np.full((corr.shape[0],), True, dtype=bool)
        for i in range(corr.shape[0]):
            for j in range(i + 1, corr.shape[0]):
                if corr.iloc[i, j] >= 0.5:
                    if columns[j]:
                        columns[j] = False
        selected_columns = data.columns[columns]
        if number >= 2:
            data = data[selected_columns]
            selected_columns = selected_columns[1:].values
            SL = 0.3
            data_modeled, selected_columns = backwardElimination(data.iloc[:, 0:-1].values, data.iloc[:, -1].values, SL,
                                                                 selected_columns)
    print(selected_columns)
    return selected_columns


def random_forest_chunks(headers, feature_length, csv_file_location, file_name):
    # df = pd.DataFrame.from_records(values, columns=headers)
    chunk_size = 10 ** 4
    counter = 0
    # clf = RandomForestClassifier(n_estimators=1000,max_features=None,random_state= 42,max_depth=10,n_jobs=-1,oob_score=True,class_weight= "balanced",bootstrap= True)
    clf = RandomForestClassifier(n_estimators=1000, max_features=None, max_depth=10, n_jobs=-1, random_state=42,
                                 bootstrap=True)

    chunk = pd.read_csv(csv_file_location)
    # X= chunk[create_headers(feature_length)]
    # print(X.shape)
    # y = chunk['label']
    # clf.fit(X, y)
    np.random.seed(123)
    chunk = shuffle(chunk)
    data = chunk.iloc[:, 0:-1]
    corr = data.corr()
    # sns.heatmap(corr)
    # plt.show()
    columns = np.full((corr.shape[0],), True, dtype=bool)
    for i in range(corr.shape[0]):
        for j in range(i + 1, corr.shape[0]):
            if corr.iloc[i, j] >= 0.5:
                if columns[j]:
                    columns[j] = False
    selected_columns = data.columns[columns]
    print(selected_columns)
    data = data[selected_columns]

    selected_columns = selected_columns[1:].values
    SL = 0.3
    data_modeled, selected_columns = backwardElimination(data.iloc[:, 0:-1].values, data.iloc[:, -1].values, SL,
                                                         selected_columns)
    data = pd.DataFrame(data=data_modeled, columns=selected_columns)

    clf.fit(data.values, chunk['label'])
    # print(clf.feature_importances_)
    # print(clf.oob_score_)
    # print(selected_columns)
    dot_data = StringIO()
    """
    for i in range (1000):
        estimators = clf.estimators_[i]

        export_graphviz(estimators, out_file="tree.dot",
                        feature_names=selected_columns,
                        class_names=["1","0"],
                        rounded=True, proportion=False,
                        precision=2, filled=True)
        print('loop')
        call(['dot', '-Tpng', 'tree.dot', '-o', 'tree.png', '-Gdpi=600'])
        img = mpimg.imread('tree.png')
        imgplot = plt.imshow(img)
        plt.show()"""
    #  print(clf.decision_path(data.values))

    pickle.dump(clf, open(file_name, 'wb'))

    return clf, selected_columns

    # pickle.dump(clf, open(file_name, 'wb'))

    # pickle.dump(clf, open(file_name, 'wb'))


def backwardElimination(x, Y, sl, columns):
    numVars = len(x[0])
    for i in range(0, numVars):
        regressor_OLS = sm.OLS(Y, x).fit()
        maxVar = max(regressor_OLS.pvalues).astype(float)
        if maxVar > sl:
            for j in range(0, numVars - i):
                if (regressor_OLS.pvalues[j].astype(float) == maxVar):
                    x = np.delete(x, j, 1)
                    columns = np.delete(columns, j)

    regressor_OLS.summary()
    return x, columns


def k_means(headers, feature_length, csv_file_location, file_name, number_of_clusters):
    chunk_size = 10 ** 3
    kmeans = KMeans(n_clusters=10000, max_iter=10)
    c = 0
    for chunk in pd.read_csv(csv_file_location, header=0, chunksize=chunk_size):
        X = chunk[create_headers(feature_length)]
        kmeans.fit(X)


def k_means_broken_samples(headers, feature_length, csv_file_location_kmeans, file_name, number_of_clusters):
    chunk_size = 10 ** 4
    kmeans = MiniBatchKMeans(n_clusters=number_of_clusters, batch_size=chunk_size, max_iter=100, random_state=42,
                             verbose=True)
    print("entering loop")

    for i, chunk in enumerate(pd.read_csv(csv_file_location_kmeans, header=0, chunksize=chunk_size)):
        X = chunk[create_headers(feature_length)]
        kmeans.partial_fit(X)
    pickle.dump(kmeans, open(file_name, 'wb'))


def search_cost_calculation(headers, feature_length, csv_file_location_kmeans, file_name, number_of_clusters):
    chunk_size = 10 ** 4
    loaded_model = pickle.load(open(file_name, 'rb'))
    result = []
    search_cost = []
    for chunk in pd.read_csv(csv_file_location_kmeans, header=0, chunksize=chunk_size):
        X = chunk[create_headers(feature_length)]
        local_result = loaded_model.predict(X)

        result = np.append(result, local_result)
    print(result)

    for i in range(number_of_clusters):
        mask = result == i
        cost = np.sum(mask)
        search_cost.append(cost)
    return search_cost


def test_images_string(images_test_file_location):
    test_images = []
    with open(images_test_file_location, 'r') as data:
        for line in data:
            if line.startswith("se"):
                split_data = line.split(' ')
                # actual_location = images_location+'/'+split_data[0]
                test_images.append(split_data[0])
    return test_images


def make_test_data(points3D_location, database_location, images_test_file_location):
    points3D = read_points3d_binary(points3D_location)
    database = sqlite3.connect(database_location)
    cursor = database.cursor()
    test_images_id = []
    training_images_id = []

    test_images_str = test_images_string(images_test_file_location)
    cursor.execute('''SELECT image_id,name FROM IMAGES ''')
    for row in cursor:
        """image_name = row[1].split('/')
        if image_name[0]=='test':
            test_images_id.append(row[0])"""
        if row[1] in test_images_str:
            test_images_id.append(row[0])
        else:
            training_images_id.append(row[0])
    database.close()
    print('test images obtrained')
    test_images_id = np.array(test_images_id)
    training_images_id = np.array(training_images_id)
    local_image_array = add_feature_location(database_location)
    cameras = read_images_binary(image_bin_location)
    image_array = make_testing_data(cameras, local_image_array)
    print('image_array made')
    test_data_positive = []
    test_data_negative = []

    for cam in points3D:
        images_with_3d = points3D[cam].image_ids
        images_with_3d_2d = points3D[cam].point2D_idxs
        test_common = np.intersect1d(images_with_3d, test_images_id)
        if len(test_common) >= 1:
            train_common = np.intersect1d(images_with_3d, training_images_id)
            if len(train_common) >= 2:

                for common in test_common:
                    location = np.where(images_with_3d == common)
                    counter = 0
                    id_2d = images_with_3d_2d[location][0]
                    image_camera = cameras[common].point3D_ids
                    for g, i in enumerate(image_camera):
                        if i > 0:
                            counter += 1
                            if cam == i:
                                index = counter

                    image_class = image_array[common - 1]
                    descriptor = image_class.poistive_descriptor[index - 1]
                    test_data_positive.append(descriptor)
            """
            else:

                location = test_common[0]
                counter = 0
                image_camera = cameras[location].point3D_ids
                for g, i in enumerate(image_camera):
                    if i > 0:
                        counter += 1
                        if cam == i:
                            index = counter

                image_class = image_array[location - 1]
                descriptor = image_class.poistive_descriptor[index - 1]
                test_data_negative.append(descriptor)"""
    """
        else :
            for location in range(1,len(images_with_3d)+1):
                id_2d = images_with_3d_2d[location]
                image_class = image_array[location-1]
                descriptor =image_class.poistive_descriptor[id_2d]
                test_data_negative.append(descriptor)"""
    print('adding negative')
    for image in image_array:
        if image.train_test == 0:
            for descriptor in image.negative_descriptor:
                test_data_negative.append(descriptor)
    return test_data_positive, test_data_negative

    return test_data


def prediction(feature_length, test_data_location, file_name_random_forest, file_name_kmeans, search_cost, capacity,
               selected_columns):
    chunk_size = 10 ** 4
    forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    kmeans_model = pickle.load(open(file_name_kmeans, 'rb'))
    result_forest = []
    result_kmeans = []
    predict_forest = []
    prediction_accracy = 0
    for chunk in pd.read_csv(test_data_location, header=0, chunksize=chunk_size):
        X = chunk[selected_columns]
        y = chunk['label']
        X_kmeans = chunk[create_headers(feature_length)]

        kmeans_result_local = kmeans_model.predict(X_kmeans)
        forest_result_local = forest_model.predict_proba(X)
        predict_result_local = forest_model.predict(X)
        result_kmeans.append(kmeans_result_local)
        result_forest.append(forest_result_local)
        predict_forest.append(predict_result_local)

        print(result_kmeans)
    actual_cost = []
    print(result_kmeans)

    result_forest = result_forest[0]
    result_kmeans = result_kmeans[0]
    predict_forest = predict_forest[0]
    print(predict_forest)
    max_value = np.amax(search_cost)
    max_limit_pareto = max_value * 0.2
    for i in result_kmeans:
        actual_cost.append(search_cost[int(i)])
    print(len(actual_cost))
    list_for_prioritization = [(cost, prob) for prob, cost in zip(result_forest[:, 0], actual_cost)]
    print(len(list_for_prioritization))
    _, best_combination = FPTAS(len(result_forest), capacity=capacity, weight_cost=list_for_prioritization,
                                scaling_factor=100)
    print(best_combination)
    print(type(best_combination))
    best_combination = np.array(best_combination)
    best_combination = best_combination[0]
    print(type(best_combination))
    fptas_location = np.where(best_combination == 1)
    print(fptas_location)
    for i in fptas_location:
        if predict_forest[i] == 1:
            prediction_accracy += 1
    print(prediction_accracy)
    prediction_accracy = prediction_accracy / len(best_combination)
    print(prediction_accracy)

    total_cost = np.sum(actual_cost)
    pareto_costs = []
    greedy_costs = []
    Numbers = np.arange(100, 4000, 500)
    for N in Numbers:
        best_cost_greedy, _, _ = greedy_mine(N, capacity=capacity, weight_cost=list_for_prioritization)

        greedy_costs.append(best_cost_greedy)
        pareto_optimal_solution = pareto_optimal(result_forest[:, 0], actual_cost, capacity, N, max_limit_pareto)
        pareto_optimal_search_cost = pareto_optimal_solution[-1][1]
        pareto_costs.append(pareto_optimal_search_cost)

    print(pareto_costs, greedy_costs)
    pareto_costs = pareto_costs / total_cost
    greedy_costs = greedy_costs / total_cost
    print(pareto_costs)
    print(greedy_costs)
    print(Numbers)
    # sns.distplot(greedy_costs,
    #             hist_kws=dict(cumulative=True),
    #            kde_kws=dict(cumulative=True))
    plt.show()
    plt.subplot()
    # bins_ = len(pareto_costs)-1
    # n, bins, patches =plt.hist(greedy_costs,bins= bins_, histtype= 'bar', cumulative = True,density=True, label= 'Greedy' )
    x = pareto_costs
    # print(x)
    # plt.plot(pareto_costs.cumsum(),bins,label= 'Pareto optimal')
    plt.plot(pareto_costs, Numbers, label='Pareto optimal')
    plt.plot(greedy_costs, Numbers, label="Greedy")
    plt.legend()
    plt.show()


"""

def prediction_forest(headers, feature_length, csv_file_location_test, file_name_random_forest, clf, file_name,selected_col):
    chunk_size = 10 ** 4
    forest_model = clf
    # forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    result_forest = []
    number_axis = 11
    positive = np.zeros(number_axis)
    negative = np.zeros(number_axis)
    positive_truth = np.zeros(number_axis)
    negative_truth = np.zeros(number_axis)
    total = 0
    model_accuracy = 0
    chunk_accuracy = 0
    chunk_total = 0
    sum=0
    print(selected_col)
    for chunk in pd.read_csv(csv_file_location_test, header=0, chunksize=chunk_size):
        X=chunk[selected_col]
        y = np.array(chunk['label'])
        forest_result_class = forest_model.predict(X)

        forest_result_local = forest_model.predict_proba(X)

        numpy_local = np.array(forest_result_class)
        if np.argmax(forest_result_local,axis=1).all() == numpy_local.all():
            print('true')
        else:
            print(np.argmax(forest_result_local,axis=1),numpy_local)
            print('false')
        y = np.transpose(y)
        sum+= np.sum(y)
        forest_result_local = forest_result_local*100
        array = forest_result_class == y
        chunk_accuracy += np.count_nonzero(forest_result_class == y)
        chunk_total += np.shape(forest_result_class)[0]
        print(chunk_accuracy / chunk_total, 'size', np.shape(forest_result_class)[0], 'chunk acc', chunk_accuracy)


        for number, prob in enumerate(forest_result_local):

            total += 1
            truth = y[number]
            classified = np.argmax(prob)
            if classified==0:
                classified=1
            elif classified ==1:
                classified=0
            prob_positive = prob[0]
            prob_negative = prob[1]
            positve_index = int(round(prob_positive /10))
            negative_index = int(round(prob_negative / 10))
            if truth == 1:

                positive_truth[positve_index] += 1
                if truth == classified:
                    positive[positve_index] += 1

                    model_accuracy += 1
            if truth == 0:
                negative_truth[negative_index] += 1
                if truth == classified:
                    negative[negative_index] += 1


                    model_accuracy += 1
     # print(prob/10,'positive',classified,truth,np.argmax(prob))
    # print(prob/10,'negative',classified,truth,np.argmax(prob))
    print(model_accuracy / total, total)
    print(positive, negative, positive_truth, negative_truth)
    accuracy_negative = []
    accuracy_positve = []
    print(sum)
    for i in range(number_axis):
        if positive[i]:
            accuracy_positve.append(positive[i] / positive_truth[i])
        else:
            accuracy_positve.append(0)
        if negative[i] > 0:
            accuracy_negative.append(negative[i] / negative_truth[i])
        else:
            accuracy_negative.append(0)
    x_axis = np.arange(number_axis)
    x_axis = x_axis / 10

    fig, ax = plt.subplots()
    line = ax.plot(x_axis, accuracy_positve, label='positve')
    line2 = ax.plot(x_axis, accuracy_negative, label='negative')
    ax.legend()
    plt.xlabel('probability from random forest')
    plt.ylabel('percentage of matches')
    plt.title('Random_forest n_estimator =1000 , max_features = number of features')
    plt.show()
    pickle.dump(clf, open(file_name, 'wb'))


"""


def add_descriptors_to_image_array(image_array, cameras):
    for rand, cam in enumerate(cameras):

        for h, k in enumerate(cameras[cam].point3D_ids):

            if k >= 0:
                id = cameras[cam].xys[h]
                image_array[cam - 1].add_positve(id[0], id[1])

        # image_array[cam - 1].add_negative()
    return image_array


"""def final_predict(feature_length, file_name_random_forest, file_name_kmeans, search_cost, capacity,
                  selected_columns, image_array, N):
    forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    kmeans_model = pickle.load(open(file_name_kmeans, 'rb'))
    best_costs = np.zeros(4)
    time_track = np.zeros(3)
    list_cost = []
    ###parameter for pareto optimal
    max_limit_pareto = np.amax(search_cost) * 0.1
    ## creating loop of the image_Array
    headers = create_headers(feature_length)
    number_of_test_images = 0
    for image in image_array:
        if image.train_test == 1:
            number_of_test_images += 1
            print(number_of_test_images)
            # making data frame
            image_Data_frame = pd.DataFrame(image.descriptor, columns=headers)
            X = image_Data_frame[selected_columns]
            print(len(image.poistive_descriptor))
            X_kmeans = image_Data_frame[headers]
            # prediction
            result_kmeans = kmeans_model.predict(X_kmeans)
            result_forest = forest_model.predict_proba(X)
            # make search cost
            actual_cost = []
            for i in result_kmeans:
                actual_cost.append(search_cost[int(i)])
            total_cost = np.sum(actual_cost)
            # combine for prioritization
            list_for_prioritization = [(cost, prob) for prob, cost in zip(result_forest[:, 0], actual_cost)]
            time_greedy_start = time.time()
            best_cost_greedy, _, _ = greedy_mine(N, capacity=capacity, weight_cost=list_for_prioritization)
            time_greedy_end = time.time()
            print('fptas')
            time_fptas_start = time.time()
            best_cost_fptas, _ = FPTAS(len(result_forest), capacity=capacity, weight_cost=list_for_prioritization,
                                       list_limit=N,
                                       scaling_factor=100)
            time_fptas_end = time.time()
            pareto_optimal_solution = pareto_optimal(result_forest[:, 0], actual_cost, capacity, N, max_limit_pareto)
            pareto_optimal_search_cost = pareto_optimal_solution[-1][1]
            time_ranking_start = time.tine()
            best_cost_ranking = average_ranking(N, list_prioritizatoin=list_for_prioritization, capacity=capacity)
            time_ranking_end = time.time()
            ### first greedy, then fptas then ranking, then pareto
            best_costs += np.array([best_cost_greedy, best_cost_fptas, best_cost_ranking, pareto_optimal_search_cost])
            time_track += np.array([time_greedy_end - time_greedy_start, time_fptas_end - time_fptas_start,
                                    time_ranking_end - time_ranking_start])
            list_cost.append(best_costs)

    ##plotting
    y = np.arange(1, number_of_test_images + 1) / number_of_test_images + 1
    best_costs = np.array(best_costs)
    plt.subplot()
    ###greedy
    plt.plot(best_costs[:, 0], y, label='greedy')
    ####fptas
    plt.plot(best_costs[:, 1], y, label='fptas')
    ####ranking
    plt.plot(best_costs[:, 2], y, label='ranking_average')
    ####pareto
    plt.plt(best_costs[:, 3], y, label='pareto optimal')
    plt.xlabel('Search cost')
    plt.ylabel('Percentage of test images')
    plt.title('Greedy time={},FPTAS time ={},Ranking_time={}'.format(time_track[0], time_track[1], time_track[2]))
    plt.legend
    plt.show()"""


def ratio_test(headers, selected_colums, data_frame, k_means_model):
    """
    Applys lowes ratio test
    :param headers: headers for descriptors
    :param data_frame: a datafram of descriptors
    :param k_means_model: k means model used for cluster
    :return: modiefied X based on ratio test
    """
    X = data_frame[headers]
    distances = k_means_model.transform(X)
    sorted_array = np.sort(distances)
    best_distance = sorted_array[:, -1]
    second_best_distance = sorted_array[:, -2]
    ratio_array = np.divide(second_best_distance, best_distance)
    rows_to_be_deleted = np.where(ratio_array > 0.7)[0]
    print(len(rows_to_be_deleted))
    new_data = data_frame.drop(rows_to_be_deleted, axis=0)
    X = new_data[headers]
    X_forest = new_data[selected_columns]
    return X_forest, X


def fptas(values, weights, n_items, capacity, scaling_factor):
    # scaling_factor = (correctness* n_items)/max_cost
    new_capacity = int(float(capacity) / scaling_factor)
    new_weight_cost = [int(round(float(weight) / scaling_factor)) for weight in weights]

    return knapsack_dp(values, new_weight_cost, n_items, new_capacity)


def knapsack_dp(values, weights, n_items, capacity, return_all=False):
    check_inputs(values, weights, n_items, capacity)

    table = np.zeros((n_items + 1, capacity + 1), dtype=np.float32)
    keep = np.zeros((n_items + 1, capacity + 1), dtype=np.float32)

    for i in range(1, n_items + 1):
        for w in range(0, capacity + 1):
            wi = weights[i - 1]  # weight of current item
            vi = values[i - 1]  # value of current item
            if (wi <= w) and (vi + table[i - 1, w - wi] > table[i - 1, w]):
                table[i, w] = vi + table[i - 1, w - wi]
                keep[i, w] = 1
            else:
                table[i, w] = table[i - 1, w]

    picks = []
    K = capacity

    for i in range(n_items, 0, -1):
        if keep[i, K] == 1:
            picks.append(i)
            K -= weights[i - 1]

    picks.sort()
    picks = [x - 1 for x in picks]  # change to 0-index

    # if return_all:
    #  max_val = table[n_items,capacity]
    # return picks,max_val
    return picks


def check_inputs(values, weights, n_items, capacity):
    # check variable type
    assert (isinstance(values, list))
    assert (isinstance(weights, list))
    assert (isinstance(n_items, int))
    assert (isinstance(capacity, int))
    # check value type
    assert (all(isinstance(val, int) or isinstance(val, float) for val in values))
    assert (all(isinstance(val, int) for val in weights))
    # check validity of value
    assert (all(val >= 0 for val in weights))
    assert (n_items > 0)
    assert (capacity > 0)


def final_predict(feature_length, file_name_random_forest, file_name_kmeans, search_cost, N,
                  selected_columns, image_array, save_location_picture):
    forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    kmeans_model = pickle.load(open(file_name_kmeans, 'rb'))
    best_numbers = np.zeros(4)
    time_track = np.zeros(3)
    list_cost = []
    ###parameter for pareto optimal
    max_limit_pareto = np.amax(search_cost) * 0.1
    scaling_factor = 10
    # scaling_factor_fptas = np.amax(search_cost)*0.5
    ## creating loop of the image_Array
    headers = create_headers(feature_length)
    number_of_test_images = 0
    for image in image_array:
        if image.train_test == 0:
            number_of_test_images += 1
            print(number_of_test_images)
            # making data frame
            if len(image.poistive_descriptor) == 0:
                descriptors = image.negative_descriptor
            else:
                descriptors = np.vstack((image.poistive_descriptor, image.negative_descriptor))
            print(len(descriptors))
            image_Data_frame = pd.DataFrame(descriptors, columns=headers)
            ##data fram modification
            # image_Data_frame = ratio_test(headers,image_Data_frame,kmeans_model)
            # X,X_kmeans = ratio_test(headers,selected_columns,image_Data_frame,kmeans_model)
            X = image_Data_frame[selected_columns]

            X_kmeans = image_Data_frame[headers]
            # prediction
            result_kmeans = kmeans_model.predict(X_kmeans)
            result_forest = forest_model.predict_proba(X)
            # make search cost
            actual_cost = []
            result_forest = list(result_forest)
            for k, i in enumerate(result_kmeans):

                if search_cost[int(i)] == 0:
                    print("found")
                    del result_forest[k]
                else:

                    actual_cost.append(search_cost[int(i)])
            total_cost = np.sum(actual_cost)
            # combine for prioritization
            result_forest = np.array(result_forest)
            list_for_prioritization = [(cost, prob) for prob, cost in zip(result_forest[:, 0], actual_cost)]
            time_greedy_start = time.time()
            solution_greedy = greedy_mine(N=N, weight_cost=list_for_prioritization)
            time_greedy_end = time.time()
            time_search_start = time.time()
            solution_search = ranking_mine(N=N, weight_cost=list_for_prioritization)
            time_search_end = time.time()
            print('greedy over')
            # time_fptas_start = time.time()
            # weights_fptas = [cost for cost in actual_cost]
            # values_fptas = [prob for prob in result_forest[:, 0]]
            # picks = fptas(weights=weights_fptas,values=values_fptas,n_items=len(weights_fptas),capacity=capacity,scaling_factor=scaling_factor)
            print('fptas')
            # _, fptas_N= FPTAS(len(result_forest), capacity=capacity, weight_cost=list_for_prioritization,scaling_factor=scaling_factor_fptas)
            # time_fptas_end = time.time()
            # print(time_fptas_end-time_fptas_start)
            # fptas_N = len(picks)
            # print("fptas")
            solution_pareto = pareto_optimal(result_forest[:, 0], actual_cost, N=N, limit=max_limit_pareto)

            print('pareto over')
            time_ranking_start = time.time()
            solution_average = average_ranking(list_prioritizatoin=list_for_prioritization, N=N)
            time_ranking_end = time.time()
            ### first greedy, then fptas then ranking, then pareto
            best_numbers = np.array([solution_greedy[0], solution_average[0], solution_pareto[0],solution_search[0]])
            time_track += np.array([time_greedy_end - time_greedy_start,
                                    time_ranking_end - time_ranking_start,time_search_end-time_search_start])
            list_cost.append(np.copy(best_numbers))

    ##plotting

    y = np.arange(1, number_of_test_images + 1) / number_of_test_images
    list_cost = np.array(list_cost)
    print(np.size(list_cost), np.size(y), list_cost, y)
    save_location_picture_N = save_location_picture + "N_no_Average.png"
    save_location_picture_average = save_location_picture + "N_average.png"
    plt.figure(figsize=(10,10))
    ###greedy
    plt.plot(np.sort(list_cost[:, 0]), y, label='Greedy Approach')
    ####ranking
    plt.plot(np.sort(list_cost[:, 1]), y, label='Average Ranking')
    ####pareto
    plt.plot(np.sort(list_cost[:, 2]), y, label='pareto optimal')
    plt.plot(np.sort(list_cost[:, 3]), y, label='Search cost ranking')
    # plt.plot(list_cost[:, 3], y, label='FPTAS')
    plt.xlabel('Search Cost')
    plt.ylabel('Percentage of test images')
    plt.title('Greedy time={:10.2f},Ranking_time={:10.2f}, Search_time = {:10.2f}'.format(time_track[0], time_track[1],time_track[2]))
    plt.legend()
    plt.savefig(save_location_picture_N)
    plt.close()
    plt.figure()
    greedy_divide = np.divide(list_cost[:, 0], list_cost[:, 2])
    average_divide = np.divide(list_cost[:, 1], list_cost[:, 2])
    plt.plot(greedy_divide, y, label='greedy')
    plt.plot(average_divide, y, label='ranking_average')
    plt.xlabel('Capacity/pareto optimal capacity')
    plt.ylabel('Percentage of test images')
    plt.legend()
    plt.savefig(save_location_picture_average)


"""
def final_predict(feature_length, file_name_random_forest, file_name_kmeans, search_cost, capacity,
                  selected_columns, image_array,save_location_picture):
    forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    kmeans_model = pickle.load(open(file_name_kmeans, 'rb'))
    best_numbers = np.zeros(3)
    time_track = np.zeros(3)
    list_cost = []
    ###parameter for pareto optimal
    max_limit_pareto = np.amax(search_cost) * 0.1
    scaling_factor_fptas = np.amax(search_cost)*0.7
    ## creating loop of the image_Array
    headers = create_headers(feature_length)
    number_of_test_images = 0
    for image in image_array:
        if image.train_test == 0:
            number_of_test_images += 1
            print(number_of_test_images)
            # making data frame
            if len(image.poistive_descriptor)==0:
                descriptors = image.negative_descriptor
            else :
                descriptors = np.vstack((image.poistive_descriptor,image.negative_descriptor))
            print(len(descriptors))
            image_Data_frame = pd.DataFrame(descriptors, columns=headers)

            X = image_Data_frame[selected_columns]

            X_kmeans = image_Data_frame[headers]
            # prediction
            result_kmeans = kmeans_model.predict(X_kmeans)
            result_forest = forest_model.predict_proba(X)
            # make search cost
            actual_cost = []
            for i in result_kmeans:
                actual_cost.append(search_cost[int(i)])
            total_cost = np.sum(actual_cost)
            # combine for prioritization
            list_for_prioritization = [(cost, prob) for prob, cost in zip(result_forest[:, 0], actual_cost)]
            time_greedy_start = time.time()
            _, _, greedy_N = greedy_mine(capacity=capacity, weight_cost=list_for_prioritization)
            time_greedy_end = time.time()
            print('greedy over')
            time_fptas_start = time.time()
            _, fptas_N= FPTAS(len(result_forest), capacity=capacity, weight_cost=list_for_prioritization,scaling_factor=scaling_factor_fptas)
            time_fptas_end = time.time()
            #pareto_optimal_solution = pareto_optimal(result_forest[:, 0], actual_cost, capacity, max_limit_pareto)
            #pareto_optimal_N= pareto_optimal_solution[-1][2]
            print('pareto over')
            time_ranking_start = time.time()
            average_N = average_ranking( list_prioritizatoin=list_for_prioritization, capacity=capacity)
            time_ranking_end = time.time()
            ### first greedy, then fptas then ranking, then pareto
            best_numbers = np.array([greedy_N, average_N,fptas_N])
            print(best_numbers)

            time_track += np.array([time_greedy_end - time_greedy_start,
                                    time_ranking_end - time_ranking_start,time_fptas_end-time_fptas_start])
            list_cost.append(np.copy(best_numbers))

    ##plotting

    y = np.arange(1, number_of_test_images+1 ) / number_of_test_images
    list_cost = np.array(list_cost)
    print(np.size(list_cost),np.size(y),list_cost,y)
    plt.figure()
    ###greedy
    plt.plot(list_cost[:, 0], y, label='greedy')
    ####ranking
    plt.plot(list_cost[:, 1], y, label='ranking_average')
    ####pareto
    #plt.plot(list_cost[:, 2], y, label='pareto optimal')
    plt.plot(list_cost[:, 2], y, label='ranking_average')
    plt.xlabel('Search cost')
    plt.ylabel('Percentage of test images')
    plt.title('Greedy time={},Ranking_time={},FPTAS_time ={},capacity={}'.format(time_track[0], time_track[1],time_track[2],capacity))
    plt.legend()
    plt.savefig(save_location_picture)
    plt.close()
    plt.show()"""


def prediction_forest(headers, feature_length, csv_file_location_test, file_name_random_forest, clf, file_name,
                      selected_col):
    chunk_size = 10 ** 4
    forest_model = clf
    # forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    result_forest = []
    number_axis = 11
    positive = np.zeros(number_axis)
    negative = np.zeros(number_axis)
    total = 0
    model_accuracy = 0
    chunk_accuracy = 0
    chunk_total = 0
    sum = 0
    #####
    local_positive = np.zeros(number_axis)
    local_negative = np.zeros(number_axis)
    local_prob_positive = np.zeros(number_axis)
    local_prob_negative = np.zeros(number_axis)
    #####
    print(selected_col)
    for chunk in pd.read_csv(csv_file_location_test, header=0, chunksize=chunk_size):
        X = chunk[selected_col]
        y = np.array(chunk['label'])
        forest_result_class = forest_model.predict(X)

        forest_result_local = forest_model.predict_proba(X)

        numpy_local = np.array(forest_result_class)
        """if np.argmax(forest_result_local,axis=1).all() == numpy_local.all():
            print('true')
        else:
            print(np.argmax(forest_result_local,axis=1),numpy_local)
            print('false')"""
        y = np.transpose(y)
        sum += np.sum(y)
        forest_result_local = forest_result_local * 100
        array = forest_result_class == y
        chunk_accuracy += np.count_nonzero(forest_result_class == y)
        chunk_total += np.shape(forest_result_class)[0]
        print(chunk_accuracy / chunk_total, 'size', np.shape(forest_result_class)[0], 'chunk acc', chunk_accuracy)

        for number, prob in enumerate(forest_result_local):

            total += 1
            truth = y[number]
            classified = forest_result_class[number]
            """classified = np.argmax(prob)
            if classified==0:
                classified=1
            elif classified ==1:
                classified=0"""
            prob_positive = prob[0]
            prob_negative = prob[1]
            positve_index = int(round(prob_positive / 10))
            negative_index = int(round(prob_negative / 10))
            ######
            local_prob_negative[negative_index] += 1
            local_prob_positive[positve_index] += 1
            if truth == classified:
                local_negative[negative_index] += 1
                local_positive[positve_index] += 1
                model_accuracy += 1
            #####
            #####
    print(local_negative, local_positive)

    # print(prob/10,'positive',classified,truth,np.argmax(prob))
    # print(prob/10,'negative',classified,truth,np.argmax(prob))
    print(model_accuracy / total, total)
    accuracy_negative = []
    accuracy_positve = []
    print(sum)
    for i in range(number_axis):
        if local_positive[i]:
            accuracy_positve.append(local_positive[i] / local_prob_positive[i])
        else:
            accuracy_positve.append(0)
        if local_negative[i] > 0:
            accuracy_negative.append(local_negative[i] / local_prob_negative[i])
        else:
            accuracy_negative.append(0)
    x_axis = np.arange(number_axis)
    x_axis = x_axis / 10

    fig, ax = plt.subplots()
    line = ax.plot(x_axis, accuracy_positve, label='positve')

    line2 = ax.plot(x_axis, accuracy_negative, label='negative')
    ax.legend()
    plt.xlabel('probability from random forest')
    plt.ylabel('percentage of matches')
    plt.title('Random_forest n_estimator =1000 , max_features = number of features')
    plt.show()
    pickle.dump(clf, open(file_name, 'wb'))


"""def pareto_optimal(result_forest, actual_cost, capacity, limit):
    parameter_to_cost_skip = 2
    pareto_optimal_solution = []
    pareto_optimal_old = []
    pareto_optimal_dub = []
    points = [[prob, cost] for prob, cost in zip(result_forest, actual_cost)]
    number_of_points = len(points)

    for i in range(number_of_points):
            cost = points[i][1]
            prob = points[i][0]
            number = 1
            if prob == 0.0 or cost >= limit:

                continue
            else:
                pareto_optimal_old = pareto_optimal_solution
                pareto_optimal_dub = []
                old_number = len(pareto_optimal_solution)
                pareto_optimal_dub.append([prob, cost,number])
                for k in range(old_number):
                    if pareto_optimal_solution[k][1] <= capacity:
                        old_prob = prob + pareto_optimal_solution[k][0]
                        old_cost = cost + pareto_optimal_solution[k][1]
                        temp_number = 1+ pareto_optimal_solution[k][2]
                        pareto_optimal_dub.append([old_prob, old_cost,temp_number])
                pareto_optimal_solution = []
                sol_temp = pareto_optimal_dub + pareto_optimal_old
                sol_temp = sorted(sol_temp, key=itemgetter(1))
                last_index = 0
                if len(sol_temp) >= 1:
                    for i in range(1, len(sol_temp)):
                        last_item = sol_temp[last_index]
                        present_item = sol_temp[i]
                        if last_item[0] < present_item[0]:
                            if last_item[1] < present_item[1]:
                                pareto_optimal_solution.append(last_item)
                                last_index = i
                if last_index < len(sol_temp):
                    pareto_optimal_solution.append(sol_temp[last_index])
    return pareto_optimal_solution"""


def pareto_optimal(result_forest, actual_cost, N, limit):
    parameter_to_cost_skip = 2
    pareto_optimal_solution = []
    pareto_optimal_old = []
    pareto_optimal_dub = []
    points = [[prob, cost] for prob, cost in zip(result_forest, actual_cost)]
    number_of_points = len(result_forest)
    N = np.array(N)
    N = np.where(N >= number_of_points, number_of_points, N)
    counter_for_N = 0
    first_N = N[counter_for_N]
    final_element = N[-1]
    solutions = []

    for i in range(number_of_points):

        cost = points[i][1]
        prob = points[i][0]
        if prob == 0.0 or cost >= limit:

            continue
        else:
            pareto_optimal_old = pareto_optimal_solution
            pareto_optimal_dub = []
            old_number = len(pareto_optimal_solution)
            pareto_optimal_dub.append([prob, cost])
            for k in range(old_number):
                # if pareto_optimal_solution[k][1] <= capacity:
                old_prob = prob + pareto_optimal_solution[k][0]
                old_cost = cost + pareto_optimal_solution[k][1]
                pareto_optimal_dub.append([old_prob, old_cost])
            pareto_optimal_solution = []
            sol_temp = pareto_optimal_dub + pareto_optimal_old
            sol_temp = sorted(sol_temp, key=itemgetter(1))
            last_index = 0
            if len(sol_temp) >= 1:
                for i in range(1, len(sol_temp)):
                    last_item = sol_temp[last_index]
                    present_item = sol_temp[i]
                    if last_item[0] < present_item[0]:
                        if last_item[1] < present_item[1]:
                            pareto_optimal_solution.append(last_item)
                            last_index = i
            if last_index < len(sol_temp):
                pareto_optimal_solution.append(sol_temp[last_index])

        if i + 1 >= first_N:
            for numbers in range(len(np.where(N == first_N)[0])):
                solutions.append(pareto_optimal_solution[-1][1])
                counter_for_N += 1

            if final_element == first_N:

                return solutions
            else:
                first_N = N[counter_for_N]

    if len(solutions) != len(N):
        for i in range(len(N) - len(solutions)):
            solutions.append(pareto_optimal_solution[-1][1])
    return solutions


def get_image_descriptors(image_array, cameras):
    for rand, cam in enumerate(cameras):

        for h, k in enumerate(cameras[cam].point3D_ids):

            if k >= 0:
                id = cameras[cam].xys[h]
                image_array[cam - 1].add_positve(id[0], id[1])

        image_array[cam - 1].add_negative()
    test_data = []
    for image in image_array:
        if image.train_test == 1:
            for descriptor in image.poistive_descriptor:
                test_data.append(descriptor)

            for descriptor in image.negative_descriptor:
                test_data.append(descriptor)
            return test_data


def average_ranking(N, list_prioritizatoin):
    # cost , prob
    ranking_cost = [(index, item[0]) for index, item in enumerate(list_prioritizatoin)]
    ranking_prob = [(index, item[1]) for index, item in enumerate(list_prioritizatoin)]
    ranking_cost = np.array(sorted(ranking_cost, key=lambda x: x[1], reverse=False))
    ranking_prob = np.array(sorted(ranking_prob, key=lambda x: x[1], reverse=False))
    ranked_array = []
    number_of_points = len(list_prioritizatoin)
    N = np.array(N)
    N = np.where(N >= number_of_points, number_of_points, N)
    counter_for_N = 0
    first_N = N[counter_for_N]
    final_element = N[-1]
    solutions = []

    for i in range(len(list_prioritizatoin)):
        local_rank_cost = np.argwhere(ranking_cost[:, 0] == i)
        local_rank_prob = np.argwhere(ranking_prob[:, 0] == i)
        average = local_rank_cost + local_rank_prob / 2
        ranked_array.append((i, average))
    ranked_array = np.array(sorted(ranked_array, key=lambda x: x[1], reverse=False))
    return_rank = ranked_array[:, 0]
    local_capacity = 0
    for number_of_matches, i in enumerate(return_rank):
        i = int(i)
        local_capacity += list_prioritizatoin[i][0]
        if number_of_matches + 1 == first_N:
            for k in range(len(np.where(N == first_N)[0])):
                solutions.append(local_capacity)
                counter_for_N += 1
            if first_N == final_element:
                return solutions
            else:
                first_N = N[counter_for_N]

    print("you fucked up")
    return solutions


def greedy_mine(N, weight_cost):
    # input cost,prob
    ratios = [(index, item[1] / float(item[0])) for index, item in enumerate(weight_cost)]
    ratios = sorted(ratios, key=lambda x: x[1], reverse=True)
    best_comb = []
    number_of_points = len(weight_cost)
    N = np.array(N)
    N = np.where(N >= number_of_points, number_of_points, N)
    counter_for_N = 0
    first_N = N[counter_for_N]
    final_element = N[-1]
    solutions = []

    best_cost = 0
    for i in range(number_of_points):
        index = ratios[i][0]
        best_cost += weight_cost[index][0]
        if i + 1 == first_N:
            for k in range(len(np.where(N == first_N)[0])):
                solutions.append(best_cost)
                counter_for_N += 1
            if first_N == final_element:
                return solutions
            else:
                first_N = N[counter_for_N]
    print("you fucked up")

    return solutions

def ranking_mine(N, weight_cost):
    # input cost,prob
    ratios = [(index, item[0]) for index, item in enumerate(weight_cost)]
    # ranking_prob = [(index, item[1]) for index, item in enumerate(list_prioritizatoin)]
    ratios = np.array(sorted(ratios, key=lambda x: x[1], reverse=False))
    # ranking_prob = np.array(sorted(ranking_prob, key=lambda x: x[1], reverse=False))
    best_comb = []
    number_of_points = len(weight_cost)
    N = np.array(N)
    N = np.where(N >= number_of_points, number_of_points, N)
    counter_for_N = 0
    first_N = N[counter_for_N]
    final_element = N[-1]
    solutions = []

    best_cost = 0
    for i in range(number_of_points):
        index = ratios[i][0]
        best_cost += weight_cost[index][0]
        if i + 1 == first_N:
            for k in range(len(np.where(N == first_N)[0])):
                solutions.append(best_cost)
                counter_for_N += 1
            if first_N == final_element:
                return solutions
            else:
                first_N = N[counter_for_N]
    print("you fucked up")

    return solutions



def handle_data_for_test_image(positive, feature_length, csv_file_location_kmeans):
    print('data_handling')
    headers = create_headers(feature_length)
    headers.append('label')
    # shape_training_labels = np.shape(training_labels[0])
    # samples = np.append(training_samples, training_labels, axis=1)
    # samples_kmeans = random.sample(samples,100000)
    with open(csv_file_location_kmeans, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for j, i in enumerate(positive):
            # values.append(tuple(k))
            writer.writerow(i)

    # for i in samples:
    # values.append(tuple(i))
    csvfile.close()

    return headers


cameras = read_images_binary(image_bin_location)
# image_array = get_details_from_database()
image_array = add_feature_location(database_locatiom, images_test_file_location)

print('task1 complete')
positive, negative = make_training_data(cameras, image_array)
print('task2 complete')
"""
headers = handle_data(positive, negative, feature_length, csv_file_location_400000)
print('3')
headers=handle_data_for_kmeans(positive,negative,feature_length,csv_file_location_kmeans)
print('4')
test_data_positve,test_data_negative = make_test_data(point3D_location_overall,database_locatiom,images_test_file_location)
headers = handle_data(test_data_positve,test_data_negative,feature_length,csv_file_location_kmeans_test)
print('all the csv files are ready')"""

# test_data = get_image_descriptors(image_array=image_array,cameras=cameras)
# headers = handle_data_for_test_image(test_data,feature_length=feature_length,csv_file_location_kmeans=csv_file_test_image)

###remove ttis
# headers = create_headers(feature_length)
# headers.append('label')

# clf,selected_columns=random_forest_chunks(headers,feature_length,csv_file_location_400000,file_name_random_forest )
# headers = create_headers(feature_length)
# k_means(headers,feature_length,csv_file_location,file_name)
# selected_columns = ['1', '2', '3' ,'4' ,'5' ,'7' ,'8' ,'12' ,'15' ,'16' ,'19' ,'20' ,'21' ,'24', '28', '38', '49', '66' ,'81', '95']
print("kmeans")
print("random forest saved")
# k_means_broken_samples(headers,feature_length,csv_file_location_kmeans,file_name_kmeans,number_of_clusters)
# search_cost = search_cost_calculation(headers, feature_length, csv_file_location_kmeans, file_name_kmeans, number_of_clusters)

# print(search_cost)
# clf = pickle.load(open(file_name_random_forest, 'rb'))

# prediction_forest(headers,feature_length,csv_file_location_kmeans_test,file_name_random_forest,clf,file_name= file_name_random_forest,selected_col=selected_columns)
# prediction (headers,feature_length,csv_file_test_image,file_name_random_forest,file_name_kmeans,number_of_clusters,search_cost,capacity)
# prediction (feature_length=feature_length,test_data_location=csv_file_test_image,file_name_random_forest=file_name_random_forest,file_name_kmeans=file_name_kmeans,search_cost=search_cost,capacity=max_cost,selected_columns=selected_columns)
###remove this
headers = create_headers(feature_length)
headers.append('label')
###
# clf,selected_columns=random_forest_chunks(headers,feature_length,csv_file_location_400000,file_name_random_forest )
# k_means(headers,feature_length,csv_file_location,file_name)
# selected_columns = ['1', '2', '3', '4', '5', '7', '8', '12', '15', '16', '19', '20', '21', '24', '28', '38', '49', '66',
#                   '81', '95']
print("kmeans")
print("random forest saved")

selected_columns = create_headers(feature_length)
csv_file_location_kmeans = "/home/earlfernando/shopfacade/train_kmeans.csv"
file_name_kmeans = "/home/earlfernando/shopfacade/test_model_kmeans.sav"
file_name_random_forest = "/home/earlfernando/shopfacade/dataset_full/noFeature/N=50max_depth=1000min_leaf=1.sav"

save_location_picture = "/home/earlfernando/shopfacade/best_plot"
# k_means(headers,feature_length,csv_file_location_kmeans,file_name_kmeans)
# k_means_broken_samples(headers,feature_length,csv_file_location_kmeans,file_name_kmeans,number_of_clusters)

search_cost = search_cost_calculation(headers, feature_length, csv_file_location_kmeans, file_name_kmeans,
                                      number_of_clusters)

# print(search_cost)
# clf = pickle.load(open(file_name_random_forest, 'rb'))

# prediction_forest(headers,feature_length,csv_file_location_kmeans_test,file_name_random_forest,clf,file_name= file_name_random_forest,selected_col=selected_columns)
# prediction (headers,feature_length,csv_file_test_image,file_name_random_forest,file_name_kmeans,number_of_clusters,search_cost,capacity)
# prediction (feature_length=feature_length,test_data_location=csv_file_test_image,file_name_random_forest=file_name_random_forest,file_name_kmeans=file_name_kmeans,search_cost=search_cost,capacity=max_cost,selected_columns=selected_columns)
N_overall = [500, 700, 1000, 1500]

for i in N_overall:
    i = [i]
    save_location_picture_local = save_location_picture + str(i)

    final_predict(feature_length, file_name_random_forest, file_name_kmeans, search_cost, i, selected_columns,
                  image_array, save_location_picture_local)

""""File locations 

 Great court 
 #file_name_random_forest = "/home/earlfernando/greatCourtTrinity/dataset_20000/correlation+pvalue/N=100max_depth=10min_leaf=1.sav"
#file_name_kmeans = "/home/earlfernando/greatCourtTrinity/GreatCourt/test_model_kmeans.sav"


Old Hospital

csv_file_location_kmeans = "/home/earlfernando/oldHospital/train_kmeans.csv"
file_name_kmeans = "/home/earlfernando/oldHospital/test_model_kmeans.sav"
file_name_random_forest = "/home/earlfernando/oldHospital//dataset_full/noFeature/N=100max_depth=1000min_leaf=10.sav"

save_location_picture = "/home/earlfernando/oldHospital/best_plot"


 """

"""
#Selectkbest -Univariate selection using  chi2  statistical test for non negative values
#https://towardsdatascience.com/feature-selection-techniques-in-machine-learning-with-python-f24e7da3f36e 0.629


def random_forest_chunks(headers, feature_length, csv_file_location, file_name):
    # df = pd.DataFrame.from_records(values, columns=headers)
    chunk_size = 10 ** 4
    counter = 0
    clf = RandomForestClassifier(n_estimators=10,max_features=None,random_state= 42)
    #clf = RandomForestClassifier(n_estimators=1000,max_features=None,min_samples_leaf=10,max_depth=100,n_jobs=-1,oob_score= True,random_state= 42)
    chunk =pd.read_csv(csv_file_location, header=0)
    #X= chunk[create_headers(feature_length)]
    #y = chunk['label']
    X = chunk.iloc[:,0:128]
    print(X)
    y = chunk.iloc[:,-1]

    bestfeatures = SelectKBest(score_func=chi2, k=100)
    fit = bestfeatures.fit(X, y)
    dfscores = pd.DataFrame(fit.scores_)
    dfcolumns = pd.DataFrame(X.columns)
    featureScores = pd.concat([dfcolumns, dfscores], axis=1)
    featureScores.columns = ['Specs', 'Score']
    print(featureScores.nlargest(50, 'Score'))

    print(fit.get_support(indices = False))
    X = chunk.iloc[:,fit.get_support(indices = False)]
    y = chunk.iloc[:,-1]


    clf.fit(X, y)
    return fit.get_support(indices = False),clf






def prediction_forest(headers, feature_length, csv_file_location_test, file_name_random_forest, clf, file_name,new_headers):
    chunk_size = 10 ** 4
    forest_model = clf
    # forest_model = pickle.load(open(file_name_random_forest, 'rb'))
    result_forest = []
    positive = np.zeros(10)
    negative = np.zeros(10)
    positive_truth = np.zeros(10)
    negative_truth = np.zeros(10)
    total = 0
    model_accuracy = 0
    chunk_accuracy = 0
    chunk_total = 0
    for chunk in pd.read_csv(csv_file_location_test, header=0, chunksize=chunk_size):
        X = np.array(chunk[create_headers(feature_length)])
        X_forest = chunk.iloc[:,new_headers]
        y = np.array(chunk[['label']])
        forest_result_class = forest_model.predict(X_forest)

        forest_result_local = forest_model.predict_proba(X_forest)
        numpy_local = np.array(forest_result_local)
        y = np.transpose(y)
        y = y[0]
        array = forest_result_class == y
        chunk_accuracy += np.count_nonzero(forest_result_class == y)
        chunk_total += np.shape(forest_result_class)[0]
        print(chunk_accuracy / chunk_total, 'size', np.shape(forest_result_class)[0], 'chunk acc', chunk_accuracy)

        for number, prob in enumerate(forest_result_local):
            total += 1
            truth = y[number]
            classified = forest_result_class[number]
            prob_positive = prob[1]
            prob_negative = prob[0]
            positve_index = int(round(prob_positive * 10))-1
            negative_index = int(round(prob_negative * 10))-1
            if truth == 1:

                positive_truth[positve_index] += 1
                if truth == classified:
                    positive[positve_index] += 1
                    model_accuracy += 1
            if truth == 0:
                negative_truth[negative_index] += 1
                if truth == classified:
                    negative[negative_index] += 1
                    model_accuracy += 1

    print(model_accuracy / total, total)
    print(positive, negative, positive_truth, negative_truth)
    accuracy_negative = []
    accuracy_positve = []
    for i in range(10):
        if positive[i]:
            accuracy_positve.append(positive[i] / positive_truth[i])
        else:
            accuracy_positve.append(0)
        if negative[i] > 0:
            accuracy_negative.append(negative[i] / negative_truth[i])
        else:
            accuracy_negative.append(0)
    x_axis = np.arange(10)
    x_axis = x_axis / 10

    fig, ax = plt.subplots()
    line = ax.plot(x_axis, accuracy_positve, label='positve')
    line2 = ax.plot(x_axis, accuracy_negative, label='negative')
    ax.legend()
    plt.xlabel('probability from random forest')
    plt.ylabel('percentage of matches')
    plt.title('Random_forest n_estimator =1000 , max_features = number of features')
    plt.show()
    pickle.dump(clf, open(file_name, 'wb'))
    """

"""
65.1% accuracy

def random_forest_chunks(headers, feature_length, csv_file_location, file_name):
    # df = pd.DataFrame.from_records(values, columns=headers)
    chunk_size = 10 ** 4
    counter = 0
    clf = RandomForestClassifier(n_estimators=1000,max_features=None,random_state= 42, max_depth=10)
    #clf = RandomForestClassifier(n_estimators=1000,max_features=None,min_samples_leaf=10,max_depth=100,n_jobs=-1,oob_score= True,random_state= 42)
    chunk =pd.read_csv(csv_file_location)
    #X= chunk[create_headers(feature_length)]
    #print(X.shape)
    #y = chunk['label']
    #clf.fit(X, y)
    np.random.seed(123)
    print(chunk)
    data = chunk.iloc[:, 0:-1]
    corr =data.corr()
    sns.heatmap(corr)
    columns = np.full((corr.shape[0],), True, dtype=bool)
    for i in range(corr.shape[0]):
        for j in range(i + 1, corr.shape[0]):
            if corr.iloc[i, j] >= 0.5:
                if columns[j]:
                    columns[j] = False
    selected_columns = data.columns[columns]
    data = data[selected_columns]
    selected_columns = selected_columns[1:].values
    SL = 0.1
    data_modeled, selected_columns = backwardElimination(data.iloc[:, 0:-1].values, data.iloc[:, -1].values, SL,
                                                         selected_columns)

    data = pd.DataFrame(data=data_modeled, columns=selected_columns)
    print(data)
    clf.fit(data.values,chunk['label'])
    print(selected_columns)

    return clf,selected_columns

    #pickle.dump(clf, open(file_name, 'wb'))


    # pickle.dump(clf, open(file_name, 'wb'))


def backwardElimination(x, Y, sl, columns):
    numVars = len(x[0])
    for i in range(0, numVars):
        regressor_OLS = sm.OLS(Y, x).fit()
        maxVar = max(regressor_OLS.pvalues).astype(float)
        if maxVar > sl:
            for j in range(0, numVars - i):
                if (regressor_OLS.pvalues[j].astype(float) == maxVar):
                    x = np.delete(x, j, 1)
                    columns = np.delete(columns, j)

    regressor_OLS.summary()
    return x, columns"""

"""
def random_forest_chunks(headers, feature_length, csv_file_location, file_name):
    # df = pd.DataFrame.from_records(values, columns=headers)
    chunk_size = 10 ** 4
    counter = 0
    clf = RandomForestClassifier(n_estimators=1000,max_features=None,random_state= 42, max_depth=10)
    clf = RandomForestClassifier(n_estimators=1000,max_features=None,min_samples_leaf=10,max_depth=100,n_jobs=-1,oob_score= True,random_state= 42)
    chunk =pd.read_csv(csv_file_location)
    #X= chunk[create_headers(feature_length)]
    #print(X.shape)
    #y = chunk['label']
    #clf.fit(X, y)
    np.random.seed(123)
    print(chunk)
    data = chunk.iloc[:, 0:-1]
    corr =data.corr()
    sns.heatmap(corr)
    columns = np.full((corr.shape[0],), True, dtype=bool)
    for i in range(corr.shape[0]):
        for j in range(i + 1, corr.shape[0]):
            if corr.iloc[i, j] >= 0.5:
                if columns[j]:
                    columns[j] = False
    selected_columns = data.columns[columns]
    data = data[selected_columns]
    selected_columns = selected_columns[1:].values
    SL = 0.3
    data_modeled, selected_columns = backwardElimination(data.iloc[:, 0:-1].values, data.iloc[:, -1].values, SL,
                                                         selected_columns)
    print(selected_columns)

    data = pd.DataFrame(data=data_modeled, columns=selected_columns)
    print(data)
    clf.fit(data.values,chunk['label'])
    important_features = np.array(clf.feature_importances_)
    important_features = important_features >=0.04
    feature_header =[]

    for k,l in zip(selected_columns,important_features):
        if l:
            feature_header.append(k)
    print(feature_header)
    slf = RandomForestClassifier(n_estimators=1000,max_features= None,max_depth=10,random_state=42)
    chunk =pd.read_csv(csv_file_location, header= 0)
    X =chunk[feature_header]
    y = chunk['label']
    slf.fit(X, y)
    print(selected_columns)

    print(feature_header)

    return slf,feature_header"""














