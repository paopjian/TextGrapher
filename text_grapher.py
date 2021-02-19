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
        return [sentence for sentence in re.split(r'[？?！!。；;：:\n\r\s|]', content) if sentence]

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
    def extract_triples2(self, words, postags,ner):
        ner = [i.split('/')[0] for i in set(ner)]
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
            if rel in ['DOB']:
                sub_wd = tuple[0][0]
                verb_wd = tuple[0][1]
                obj1 = tuple[0][2]
                obj2 = tuple[0][3]

                if not sub_wd:
                    if obj1 in ner:
                        svo.append([obj1, verb_wd+obj2])
                        print(svo[-1])
                        return svo
                    if obj2 in ner:
                        svo.append([obj2, verb_wd + obj1])
                        print(svo[-1])
                        return svo

                if not obj1:
                    svo.append([sub_wd, verb_wd])
                else:
                    svo.append([sub_wd, verb_wd+obj1+obj2])
                print(svo[-1])
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
        for sent in sents:
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
                if triple:
                    triples += triple
                    ners += ner
                    ner_sents.append([words, postags])
            if ner2:
                triple = self.extract_triples2(words2, postags2,ner2)
                if triple:
                    triples2 += triple
                    ners2 += ner2
                    ner_sents2.append([words2, postags2])
        # 获取文章关键词, 并图谱组织, 这个可以做
        keywords = [i[0] for i in self.extract_keywords(words_list)]
        # key = self.parser.keyword.extract_tags3(sentence=content,allowPOS=('n', 'nr','ns', 'nz', 'PER', 'nt', 'ORG','LOC','vn'))
        keywords2 = self.parser.keyword.extract_tags2(words=words_list2,topK=10,allowPOS=('n', 'nr','ns', 'nz', 'PER', 'nt', 'ORG','LOC','vn'))
        # print(keywords2[1])
        for keyword in keywords:
            name = keyword
            cate = '关键词'
            events.append([name, cate])

        for keyword in keywords2[0]:
            if keywords2[1][keyword]>1:
                name = keyword
                cate = '关键词'
                events2.append([name, cate])
        # 对三元组进行event构建，这个可以做
        for t in triples:
            if (t[0] in keywords or t[1] in keywords) and len(t[0]) > 1 and len(t[1]) > 1:
                events.append([t[0], t[1]])
        for t in triples2:
            if (t[0] in keywords2[0] or t[1] in keywords2[0]) and len(t[0]) > 1 and len(t[1]) > 1:
                events2.append([t[0], t[1]])
        # 获取文章词频信息话，并图谱组织，这个可以做
        word_dict = [i for i in Counter([i[0] for i in words_list if i[1][0] in ['n', 'v'] and len(i[0]) > 1]).most_common()][:10]
        for wd in word_dict:
            name = wd[0]
            cate = '高频词'
            events.append([name, cate])
        for word,num in keywords2[1].items():
            if num>1:
                name = word
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
        events_entity_keyword2 = self.rel_entity_keyword(ners2, keywords2[0], subsents_seg2)
        events2 += events_entity_keyword2
        #对事件网络进行图谱化展示
        self.graph_shower.create_page(events)
        self.graph_shower.create_page(events2,'graph_show2.html')
        print(events2)

content9 = """沪浙打通首条省界“断头路”：通勤从30分钟缩短到3分钟！,新华社上海12月28日电(记者 王辰阳)连接上海市金山区和浙江省嘉善县的叶新公路新建工程28日开通。这是沪浙毗邻地区打通的首条省界“断头路”。据悉，道路通车后可有效缓解320国道的交通压力，将上海枫泾至浙江姚庄的出行时间从30分钟缩短为3分钟，给两地居民往来带来便利。     据介绍，叶新公路新建工程西起浙江省界，东至朱枫公路，全长2.24公里。该段道路设计时速为80公里/小时，双向六车道。除了道路开通，西塘来往枫泾的跨省公交线路也同步开通，将进一步提升区域公共交通的服务水平。    叶新公路新建工程的项目建设，充分体现了长三角一体化的协同优势。以道路在沪浙交界处的潮里泾大桥为例，金山、嘉善两地协商形成了“双方审批、共同出资、一方代建”的合作模式。该桥建设投入资金约5亿元，两地共同承担，由嘉善代建设。    上海市交通委主任谢峰表示，打通省界“断头路”项目是长三角一体化国家战略的重要组成部分。截至目前，上海已打通4条省界“断头路”，复兴路至曙光路、朱吕公路至善新公路等项目仍在建设中，争取尽早建成发挥社会效益。 【编辑:朱延静】"""
content = """北京顺义核酸检测采样超120万人其中90余万已出结果 均为阴性,中新网北京12月28日电 (陈杭)北京市顺义区委常委、常务副区长支现伟28日在发布会上表示，顺义区大规模核酸检测取得重要进展，13个重点地区重点领域80万人核酸检测任务已完成，截至今日15时，已完成采样1207657人，已出结果901206人，检测结果均为阴性。     支现伟强调，“三村一区”(高丽营镇张喜庄村、南法信镇西杜兰村、东海洪村，金马工业区)人员的核酸检测已全部完成，检测结果均为阴性。    结合疫情防控形势，顺义区合理调配资源，首批13个镇街功能区各保留一组采样点，其余设备资源及时支援其他地区。同时做好采样人员和物资储备，每个属地配备一名专业技术保障人员。    截至目前，13616名服务保障人员、1886名医务人员已投入到检测工作中，838个帐篷、1005个电暖气、103491个口罩、15956套防护服、59337个暖宝等物资已配备到位。    支现伟表示，顺义严格核酸检测工作流程，采取划分区域、单向通道、一米线和专人指引等严密措施，确保检测工作安全有序；开辟送检快速通道，实行专人负责，按时按点送检，进一步提高检测效率。    此外，顺义区各镇街道迅速实施一级防控措施，社区(村)卡口缩减至1-2个，严格查证、验码、测温、登记“四件套”，严防社区传播风险；各部门迅速提升各行业防控等级，加大监督检查力度，确保防控措施落实落细落到位。为加大基层防疫工作力量，抽调区内56家单位1050名干部职工支援属地防疫，1万余名党员回社区(村)报到，参与到各项防控工作中。    支现伟呼吁，实施封闭管理区域的居民，一定要注意好个人自我防护，做到足不出户；其他居民也要尽量减少流动，非必要不出京，非必要不出境，配合好社区、单位等的防疫工作。(完) 【编辑:叶攀】"""
content2 = """吉林银行原党委委员、副行长杨盛忠被开除党籍和公职,中央纪委国家监委网站讯  据吉林省纪委监委消息：日前，经吉林省委批准，吉林省纪委监委对吉林银行股份有限公司原党委委员、副行长杨盛忠严重违纪违法问题进行了立案审查调查。    经查，杨盛忠利用职务上的便利，非法骗取公共财物，数额特别巨大，涉嫌贪污犯罪；利用职务上的便利，为他人谋取利益并索取、收受财物，数额特别巨大，涉嫌受贿犯罪。    杨盛忠身为党员领导干部，理想信念丧失，宗旨意识泯灭，对党不忠诚不老实，一再拒绝组织的教育和挽救；贪权敛财，滥权妄为，侵占公物；私欲膨胀，胆大妄为，攫取私利，其行为严重违反党的纪律，已涉嫌犯罪，且在党的十八大后不知止、不收敛、不收手，性质恶劣，情节严重，应予严肃处理。依据《中国共产党纪律处分条例》《中华人民共和国监察法》《中华人民共和国公职人员政务处分法》等有关规定，经吉林省纪委常委会议研究并报吉林省委批准，决定给予杨盛忠开除党籍处分；由吉林省监委给予其开除公职处分；将其涉嫌犯罪问题移送检察机关依法审查起诉，所涉财物随案移送。    杨盛忠简历     杨盛忠，男，1963年1月出生，汉族，吉林长春人， 1985年7月参加工作，1996年12月加入中国共产党，在职研究生学历。    2009年1月，任吉林银行辽源分行党委副书记、行长；    2010年8月，任吉林银行吉林分行党委书记；    2010年10月，任吉林银行行长助理兼吉林分行党委书记、行长；    2015年3月，任吉林银行行长助理兼个人金融总部总裁；    2016年9月，任吉林银行党委委员、副行长兼个人金融总部总裁；    2017年7月，任吉林银行党委委员、副行长兼总行公司金融总部总裁；    2019年12月，任吉林银行党委委员、副行长；    2020年8月，免去其吉林银行副行长职务。  (吉林省纪委监委) 【编辑:张楷欣】"""
content3= """决定给予杨盛忠开除党籍处分;由吉林省监委给予其开除公职处分,1985年7月参加工作"""
handler = CrimeMining()
handler.main(content2)