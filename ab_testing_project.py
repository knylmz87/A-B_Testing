# AB Testi ile Bidding Yöntemlerinin Dönüşümünün Karşılaştırılması

# İş Problemi

# Facebook kısa süre önce mevcut "maximum bidding" adı verilen teklif verme türüne alternatif olarak yeni bir teklif
# türü olan "average bidding"’i tanıttı. Müşterilerimizden biri olan bombabomba.com, bu yeni özelliği test etmeye karar
# verdi ve average bidding'in maximum bidding'den daha fazla dönüşüm getirip getirmediğini anlamak için bir A/B testi
# yapmak istiyor. A/B testi 1 aydır devam ediyor ve bombabomba.com şimdi sizden bu A/B testinin sonuçlarını analiz
# etmenizi bekliyor. Bombabomba.com için nihai başarı ölçütü Purchase'dır. Bu nedenle, istatistiksel testler için
# Purchase metriğine odaklanılmalıdır.

# Veri Seti Hikayesi

#Bir firmanın web site bilgilerini içeren bu veri setinde kullanıcıların gördükleri ve tıkladıkları reklam sayıları gibi
# bilgilerin yanı sıra buradan gelen kazanç bilgileri yer almaktadır. Kontrol ve Test grubu olmak üzere iki ayrı veri
# seti vardır. Bu veri setleri ab_testing.xlsx excel’inin ayrı sayfalarında yer almaktadır. Kontrol grubuna
# Maximum Bidding, test grubuna Average Bidding uygulanmıştır.

# Impression : Reklam görüntüleme sayısı
# Click : Görüntülenen reklama tıklama sayısı
# Purchase : Tıklanan reklamlar sonrası satın alınan ürün sayısı
# Earning : Satın alınan ürünler sonrası elde edilen kazanç

# Ilk olarak ilgili kutuphanelerimizi import edelim

!pip install statsmodels
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.stats.api as sms
from scipy.stats import ttest_1samp, shapiro, levene, ttest_ind, mannwhitneyu, \
    pearsonr, spearmanr, kendalltau, f_oneway, kruskal
from statsmodels.stats.proportion import proportions_ztest

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', lambda x: '%.5f' % x)

# ab_testing_data.xlsx adlı kontrol ve test grubu verilerinden oluşan veri setini okutup , Kontrol ve test grubu
# verilerini ayrı değişkenlere atayalim.

df_control = pd.read_excel('C:/Users/pc/PycharmProjects/pythonProject2/4.Hafta/ab_testing.xlsx' , sheet_name= 'Control Group')
df_control_ = df_control.copy()
df_test = pd.read_excel('C:/Users/pc/PycharmProjects/pythonProject2/4.Hafta/ab_testing.xlsx' , sheet_name= 'Test Group')
df_test_ = df_test.copy()



# Kontrol ve test grubu verilerimizi analiz edelim

def  first_look_at_data (dataframe , head = 10):
    print('####### shape #######')
    print(dataframe.shape)


    print('######## types ######')
    print(dataframe.dtypes)


    print('########## NA #######')
    print(dataframe.isnull().sum())


    print('#### statistics #####')
    print(dataframe.describe().T)

    print('##### quantiles #####')
    print(dataframe.quantile([0, 0.05, 0.50, 0.95, 0.99, 1]).T)


first_look_at_data(df_control)
first_look_at_data(df_test)

# Guven araliklarina bakalim #

sms.DescrStatsW(df_control['Impression'].dropna()).tconfint_mean()
sms.DescrStatsW(df_control['Click'].dropna()).tconfint_mean()
sms.DescrStatsW(df_control['Purchase'].dropna()).tconfint_mean()
sms.DescrStatsW(df_control['Earning'].dropna()).tconfint_mean()

sms.DescrStatsW(df_test['Impression'].dropna()).tconfint_mean()
sms.DescrStatsW(df_test['Click'].dropna()).tconfint_mean()
sms.DescrStatsW(df_test['Purchase'].dropna()).tconfint_mean()
sms.DescrStatsW(df_test['Earning'].dropna()).tconfint_mean()

# Aykiri deger varsa baskilayalim


def outlier_treshholds (dataframe , variable):
    quantile1 = dataframe[variable].quantile(0.01)
    quantile3 = dataframe[variable].quantile(0.99)
    interquantile_range = quantile3 - quantile1
    up_limit = quantile3 + 1.5 * interquantile_range
    low_limit = quantile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def replace_with_tresholds (dataframe , variable):
    low_limit , up_limit = outlier_treshholds(dataframe , variable)
    dataframe.loc[(dataframe[variable] < low_limit) , variable] = low_limit
    dataframe.loc[(dataframe[variable] > up_limit) , variable] = up_limit


for col in df_control.columns:
    replace_with_tresholds(df_control , col)

for col in df_test.columns:
    replace_with_tresholds(df_control , col)


df_control.describe().T
df_test.describe().T


# Kontrol ve test grubu verilerini birlestirelim.


df_control.columns = [col + '_control' for col in df_control.columns]
df_test.columns = [col + '_test' for col in df_test.columns]

df = pd.concat([df_control , df_test] , axis=1)
df.head()

# Ilk olarak hipotezimizi tanimlayalim

#   H0 : M1 = M2 : 'average bidding' ve 'maximum bidding' ozelliklerinin satin alma sayilarinin ortalamalari arasinda istatistiksel olarak anlamli bir fark yoktur.
#   H1 : M1!= M2 : 'average bidding' ve 'maximum bidding' ozelliklerinin satin alma sayilarinin ortalamalari arasinda istatistiksel olarak anlamli bir fark vardir.

# Kontrol ve test grubu için purchase (kazanç) ortalamalarını analiz edelim.

df[['Purchase_control' , 'Purchase_test']].mean()
# 'average bidding' ve 'maximum bidding' ozelliklerinin satin alma ssayilarinin ortalamalarina bakildiginda fark oldugu
# gorulmektedir. Fakat bu farkin tesaduf olup olmadigini test etmek ve sonucu istatistiksel olarak ispatlamak icin hipotez
# testi yapilmasi gerekmektedir.



# Hipotez testi yapılmadan önce varsayım kontrollerini yapalim.
# Bunlar Normallik Varsayımı ve Varyans Homojenliğidir.
# Kontrol ve test grubunun normallik varsayımına uyup uymadığını Purchase değişkeni üzerinden ayrı ayrı test edelim.

# Normallik Varsayımı :
# H0: Normal dağılım varsayımı sağlanmaktadır.
# H1: Normal dağılım varsayımı sağlanmamaktadır.
# p < 0.05 H0 RED , p > 0.05 H0 REDDEDİLEMEZ

# Test sonucuna göre normallik varsayımı kontrol ve test grupları için saglanip saglanmadigina bakalim ve
# elde edilen p-value değerlerini yorumlayalim.

# Bunun icin shapiro testi kullanarak normal dagilim olup olmadigini test edelim

test_stat, pvalue = shapiro(df['Purchase_control'])
print('Test Stat = %.4f, p-value = %.4f' % (test_stat, pvalue))
# p-value = 0.5891 > 0.05 oldugundan HO Reddedilemez

test_stat, pvalue = shapiro(df['Purchase_test'])
print('Test Stat = %.4f, p-value = %.4f' % (test_stat, pvalue))
# p-value = 0.1541 > 0.05 oldugundan 'Normallik Varsayimi' saglanmakta oldup HO Reddedilemez


# Varyans Homojenliği :
# H0: Varyanslar homojendir.
# H1: Varyanslar homojen Değildir.
# p < 0.05 H0 RED , p > 0.05 H0 REDDEDİLEMEZ
# Kontrol ve test grubu için varyans homojenliğinin sağlanıp sağlanmadığını Purchase değişkeni üzerinden test edelim.


# Test sonucuna göre normallik varsayımınin saglanip saglanmadigini bakalim ve
# elde edilen p-value değerlerini yorumlayalim.

test_stat , pvalue = levene(df['Purchase_control'] , df['Purchase_test'])
print('Test Stat = %.4f , p-value = %.4f' % (test_stat , pvalue))

# p-value = 0.1083 > 0.05 oldugundan 'Varyanslar Homojen' olup H0 Reddedilemez.

# Normallik varsayimi saglanmistir ve varyanslar homojendir. Bu yuzden parametrik test test olan 'ttest'ini yapalim.

# ttest (parametrik test)

test_stat , pvalue = ttest_ind(df['Purchase_control'] , df['Purchase_test'] )
print('Test Stat = %.4f , p-value = %.4f' % (test_stat , pvalue))

# p-value = 0.3493 > 0.05 oldugundan HO hipotezi reddedilemez. Yani 'maximum bidding' ve 'average bidding'
# teklif verme turleri icin purchase (satin alma) ortalamalarina bakilmis ve bu iki ozellik arasinda anlamli bir fark
# olmadigi gorulmustur.

# Sonuc olarak musteriye "average bidding" ozelligi icin yatirim yapmaya gerek olmadigi, iki ozellik arasinda anlamli
# bir fark olmadigi soylenebilir.