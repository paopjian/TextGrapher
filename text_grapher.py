#!/usr/bin/env python3
# coding: utf-8
# File: crime_mining.py
# Author: lhy<lhy_in_blcu@126.com,https://huangyong.github.io>
# Date: 18-7-24

from sentence_parser import *
import re
from collections import Counter
from GraphShow import *
from keywords_textrank import *

'''事件挖掘'''
class CrimeMining:
    def __init__(self):
        self.textranker = TextRank()
        self.parser = LtpParser()
        self.ners = ['nh', 'ni', 'ns']
        self.ners2 = ['PER', 'LOC', 'ORG','TIME']
        self.ner_dict = {
        'nh':'人物',
        'ni':'机构',
        'ns':'地名'
        }
        self.ner_dict2 = {
            'PER': '人名',
            'ORG': '机构名',
            'LOC': '地名',
            'TIME':'时间'
        }
        self.graph_shower = GraphShow()

    '''移除括号内的信息，去除噪声'''
    def remove_noisy(self, content):
        p1 = re.compile(r'（[^）]*）')
        p2 = re.compile(r'\([^\)]*\)')
        p3 = re.compile(r'【[^】]*】')
        return  p3.sub('',p2.sub('', p1.sub('', content)))

    '''收集命名实体'''
    def collect_ners(self, words, postags):
        ners = []
        for index, pos in enumerate(postags):
            if pos in self.ners:
                ners.append(words[index] + '/' + pos)
        return ners
    def collect_ners2(self, words, postags):
        ners = []
        for index, pos in enumerate(postags):
            if pos in self.ners2:
                ners.append(words[index] + '/' + pos)
        return ners
    '''对文章进行分句处理'''
    def seg_content(self, content):
        return [sentence for sentence in re.split(r'[？?！!。；;：:\n\r,，\s|]', content) if sentence]

    '''对句子进行分词，词性标注处理'''
    def process_sent(self, sent):
        words, postags = self.parser.basic_process(sent)
        return words, postags

    '''构建实体之间的共现关系'''
    def collect_coexist(self, ner_sents, ners):
        co_list = []
        for sent in ner_sents:
            words = [i[0] + '/' + i[1] for i in zip(sent[0], sent[1])]
            co_ners = set(ners).intersection(set(words))
            co_info = self.combination(list(co_ners))
            co_list += co_info
        if not co_list:
            return []
        return {i[0]:i[1] for i in Counter(co_list).most_common()}

    '''列表全排列'''
    def combination(self, a):
        combines = []
        if len(a) == 0:
            return []
        for i in a:
            for j in a:
                if i == j:
                    continue
                combines.append('@'.join([i, j]))
        return combines

    '''抽取出事件三元组'''
    def extract_triples(self, words, postags):
        svo = []
        tuples, child_dict_list = self.parser.parser_main(words, postags)
        for tuple in tuples:
            rel = tuple[-1]
            if rel in ['SBV']:
                sub_wd = tuple[1]
                verb_wd = tuple[3]
                obj = self.complete_VOB(verb_wd, child_dict_list)
                subj = sub_wd
                verb = verb_wd
                if not obj:
                    svo.append([subj, verb])
                else:
                    svo.append([subj, verb+obj])
        return svo
    def extract_triples2(self, words, postags):
        svo = []
        tuples, child_dict_list = self.parser.parser_main(words, postags)

        tuples = self.parser.fine_info(self.parser.ddparser.parse_seg([words])[0]).parse()
        for tuple in tuples:
            rel = tuple[-1]
            if rel in ['SVO']:
                sub_wd = tuple[0][0]
                verb_wd = tuple[0][1]
                obj = tuple[0][2]
                subj = sub_wd
                verb = verb_wd
                if not obj:
                    svo.append([subj, verb])
                else:
                    svo.append([subj, verb+obj])
        return svo
    '''过滤出与命名实体相关的事件三元组'''
    def filter_triples(self, triples, ners):
        ner_triples = []
        for ner in ners:
            for triple in triples:
                if ner in triple:
                    ner_triples.append(triple)
        return ner_triples

    '''根据SBV找VOB'''
    def complete_VOB(self, verb, child_dict_list):
        for child in child_dict_list:
            wd = child[0]
            attr = child[3]
            if wd == verb:
                if 'VOB' not in attr:
                    continue
                vob = attr['VOB'][0]
                obj = vob[1]
                return obj
        return ''

    '''对文章进行关键词挖掘'''
    def extract_keywords(self, words_list):
        return self.textranker.extract_keywords(words_list, 10)

    '''基于文章关键词，建立起实体与关键词之间的关系'''
    def rel_entity_keyword(self, ners, keyword, subsent):
        events = []
        rels = []
        sents = []
        ners = [i.split('/')[0] for i in set(ners)]
        keyword = [i[0] for i in keyword]
        for sent in subsent:
            tmp = []
            for wd in sent:
                if wd in ners + keyword:
                    tmp.append(wd)
            if len(tmp) > 1:
                sents.append(tmp)
        for ner in ners:
            for sent in sents:
                if ner in sent:
                    tmp = ['->'.join([ner, wd]) for wd in sent if wd in keyword and wd != ner and len(wd) > 1]
                    if tmp:
                        rels += tmp
        for e in set(rels):
            events.append([e.split('->')[0], e.split('->')[1]])
        return events


    '''利用标点符号，将文章进行短句切分处理'''
    def seg_short_content(self, content):
        return [sentence for sentence in re.split(r'[，,？?！!。；;：:\n\r\t ]', content) if sentence]

    '''挖掘主控函数'''
    def main(self, content):
        if not content:
            return []
        # 对文章进行去噪处理
        content = self.remove_noisy(content)
        # 对文章进行长句切分处理
        sents = self.seg_content(content)
        # 对文章进行短句切分处理
        subsents = self.seg_short_content(content)
        subsents_seg = []
        # words_list存储整篇文章的词频信息
        words_list = []
        # ner_sents保存具有命名实体的句子
        ner_sents = []
        ner_sents2 = []
        # ners保存命名实体
        ners = []
        ners2 = []
        # triples保存主谓宾短语
        triples = []
        triples2 = []
        # 存储文章事件
        events = []
        events2 = []
        subsents_seg2=[]
        words_list2 = []
        for sent in subsents:
            words, postags = self.process_sent(sent)
            words_list += [[i[0], i[1]] for i in zip(words, postags)]
            words2, postags2 = self.parser.lac.run(sent)
            words_list2 += [[i[0], i[1]] for i in zip(words2, postags2)]
            subsents_seg.append([i[0] for i in zip(words, postags)])
            subsents_seg2.append(words2)
            ner = self.collect_ners(words, postags)
            ner2 = self.collect_ners2(words2, postags2)
            if ner:
                triple = self.extract_triples(words, postags)
                if not triple:
                    continue
                triples += triple
                ners += ner
                ner_sents.append([words, postags])
            if ner2:
                triple = self.extract_triples2(words2, postags2)
                if not triple:
                    continue
                triples2 += triple
                ners2 += ner2
                ner_sents2.append([words2, postags2])
        # 获取文章关键词, 并图谱组织, 这个可以做
        keywords = [i[0] for i in self.extract_keywords(words_list)]
        # key = self.parser.keyword.extract_tags3(sentence=content,allowPOS=('n', 'nr','ns', 'nz', 'PER', 'nt', 'ORG','LOC','vn'))
        keywords2 = self.parser.keyword.extract_tags2(words=words_list2,topK=10,allowPOS=('n', 'nr','ns', 'nz', 'PER', 'nt', 'ORG','LOC','vn'))
        for keyword in keywords:
            name = keyword
            cate = '关键词'
            events.append([name, cate])
        for keyword in keywords2[0]:
            name = keyword
            cate = '关键词'
            events2.append([name, cate])
        # 对三元组进行event构建，这个可以做
        for t in triples:
            if (t[0] in keywords or t[1] in keywords) and len(t[0]) > 1 and len(t[1]) > 1:
                events.append([t[0], t[1]])
        for t in triples2:
            if (t[0] in keywords2 or t[1] in keywords2) and len(t[0]) > 1 and len(t[1]) > 1:
                events2.append([t[0], t[1]])
        # 获取文章词频信息话，并图谱组织，这个可以做
        word_dict = [i for i in Counter([i[0] for i in words_list if i[1][0] in ['n', 'v'] and len(i[0]) > 1]).most_common()][:10]
        for wd in word_dict:
            name = wd[0]
            cate = '高频词'
            events.append([name, cate])
        for wd in keywords2[1]:
            if wd[1]>1:
                name = wd[0]
                cate = '高频词'
                events2.append([name, cate])
        #　获取全文命名实体，这个可以做
        ner_dict = {i[0]:i[1] for i in Counter(ners).most_common()}
        for ner in ner_dict:
            name = ner.split('/')[0]
            cate = self.ner_dict[ner.split('/')[1]]
            events.append([name, cate])
        ner_dict2 = {i[0]: i[1] for i in Counter(ners2).most_common()}
        for ner in ner_dict2:
            name = ner.split('/')[0]
            cate = self.ner_dict2[ner.split('/')[1]]
            events2.append([name, cate])
        # 获取全文命名实体共现信息,构建事件共现网络
        co_dict = self.collect_coexist(ner_sents, list(ner_dict.keys()))
        co_events = [[i.split('@')[0].split('/')[0], i.split('@')[1].split('/')[0]] for i in co_dict]
        events += co_events
        co_dict2 = self.collect_coexist(ner_sents2, list(ner_dict2.keys()))
        co_events2 = [[i.split('@')[0].split('/')[0], i.split('@')[1].split('/')[0]] for i in co_dict2]
        events2 += co_events2
        #将关键词与实体进行关系抽取
        events_entity_keyword = self.rel_entity_keyword(ners, keywords, subsents_seg)
        events += events_entity_keyword
        events_entity_keyword2 = self.rel_entity_keyword(ners2, keywords2, subsents_seg2)
        events2 += events_entity_keyword2
        #对事件网络进行图谱化展示
        self.graph_shower.create_page(events)
        self.graph_shower.create_page(events2,'graph_show2.html')


content9 = """沪浙打通首条省界“断头路”：通勤从30分钟缩短到3分钟！,新华社上海12月28日电(记者 王辰阳)连接上海市金山区和浙江省嘉善县的叶新公路新建工程28日开通。这是沪浙毗邻地区打通的首条省界“断头路”。据悉，道路通车后可有效缓解320国道的交通压力，将上海枫泾至浙江姚庄的出行时间从30分钟缩短为3分钟，给两地居民往来带来便利。     据介绍，叶新公路新建工程西起浙江省界，东至朱枫公路，全长2.24公里。该段道路设计时速为80公里/小时，双向六车道。除了道路开通，西塘来往枫泾的跨省公交线路也同步开通，将进一步提升区域公共交通的服务水平。    叶新公路新建工程的项目建设，充分体现了长三角一体化的协同优势。以道路在沪浙交界处的潮里泾大桥为例，金山、嘉善两地协商形成了“双方审批、共同出资、一方代建”的合作模式。该桥建设投入资金约5亿元，两地共同承担，由嘉善代建设。    上海市交通委主任谢峰表示，打通省界“断头路”项目是长三角一体化国家战略的重要组成部分。截至目前，上海已打通4条省界“断头路”，复兴路至曙光路、朱吕公路至善新公路等项目仍在建设中，争取尽早建成发挥社会效益。 【编辑:朱延静】"""
handler = CrimeMining()
handler.main(content9)