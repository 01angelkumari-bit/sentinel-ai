from __future__ import annotations

import re
from datetime import timedelta
from enum import Enum
from statistics import mean, pstdev
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ai.dataset_context import TenantDatasetContext
from app.application.ai.dataset_analysis import analyze_business_risks, analyze_sentiment, profile_dataset, risk_markdown
from app.application.ai.model_provider import get_model_provider
from app.application.analytics.service import BusinessAnalyticsService
from app.domain.users.models import ChatConversation, ChatMessage
from app.repositories.business_analytics import BusinessAnalyticsRepository


class Intent(str, Enum):
    GREETING="greeting"; THANKS="thanks"; WELLBEING="wellbeing"; CAPABILITIES="capabilities"
    WEBSITE="website"; REPORT="report"; DATA="data"; RISK="risk"; SENTIMENT="sentiment"; UNKNOWN="unknown"


class IntentDetector:
    DATA_TERMS={"revenue","sales","order","orders","cancelled","canceled","cancellations","region","regions","product","products","customer","customers","average","total","sum","count","minimum","maximum","min","max","worst","lowest","trend","increase","decrease","decline","growth","dataset","csv","excel","file","kpi","summary","summarize","analyse","analyze"}
    @staticmethod
    def words(text:str)->set[str]: return set(re.findall(r"[a-z0-9']+",text.lower()))
    def detect(self,text:str)->Intent:
        words=self.words(text); compact=" ".join(text.lower().strip().split())
        if re.fullmatch(r"(hi|hello|hey|hiya|good (morning|afternoon|evening)|hey sentinel)[!. ]*",compact):return Intent.GREETING
        if "how are you" in compact or "how's it going" in compact:return Intent.WELLBEING
        if words & {"thanks","thank","thx"}:return Intent.THANKS
        if "what can you do" in compact or "help me" in compact or "your capabilities" in compact:return Intent.CAPABILITIES
        if words & {"sentiment","rating","ratings","feedback","review","reviews"}:return Intent.SENTIMENT
        if words & {"risk","risks","risky","worry","worried","unusual","anomaly","anomalies","recommend","recommendation","recommendations","evidence","conclusion"}:return Intent.RISK
        if words & self.DATA_TERMS:return Intent.DATA
        if words & {"sentinel","website","dashboard","upload","onboarding","login","register","account","settings"}:return Intent.WEBSITE
        if words & {"report","reports","pdf","export","download"}:return Intent.REPORT
        return Intent.UNKNOWN


class SentinelAIService:
    """Natural conversation plus deterministic, tenant-scoped data analysis."""
    def __init__(self,db:Session,organization_id:UUID,user_id:UUID)->None:
        self.db,self.organization_id,self.user_id=db,organization_id,user_id
        self.repository=BusinessAnalyticsRepository(db,organization_id)
        self.analytics=BusinessAnalyticsService(self.repository)
        self.datasets=TenantDatasetContext(db,organization_id)
        self.detector=IntentDetector()
        self.model=get_model_provider()

    def _conversation(self,conversation_id:UUID|None,question:str)->ChatConversation:
        if conversation_id:
            item=self.db.scalar(select(ChatConversation).where(ChatConversation.id==conversation_id,ChatConversation.organization_id==self.organization_id,ChatConversation.user_id==self.user_id))
            if not item:raise HTTPException(status_code=404,detail="Conversation not found")
            return item
        item=ChatConversation(organization_id=self.organization_id,user_id=self.user_id,title=question.strip().replace("\n"," ")[:80] or "New conversation");self.db.add(item);self.db.flush();return item

    @staticmethod
    def _number(value:float)->str:return f"{float(value):,.2f}"
    @staticmethod
    def _integer(value:float)->str:return f"{int(value):,}"
    @staticmethod
    def _followups()->list[str]:return ["Summarize this file","Which region has the highest revenue?","Show the top 5 customers"]

    def _normal_answer(self,intent:Intent)->tuple[str,list[str]]:
        if intent==Intent.GREETING:return "Hi! I'm Sentinel AI. How can I help you?",["What can you do?","Summarize my data","How do I generate a report?"]
        if intent==Intent.THANKS:return "You're welcome! If you'd like, I can help you explore your data, explain a KPI, or generate and understand a report.",["What can you do?","Show total revenue"]
        if intent==Intent.WELLBEING:return "I'm doing well and ready to help. I can guide you through Sentinel or analyze your organization's uploaded business data.",["What can you do?","Summarize my data"]
        if intent==Intent.CAPABILITIES:return "I can help you use Sentinel, understand dashboards and KPIs, analyze uploaded CSV or Excel datasets, compare products, regions and customers, explain trends, and help with saved PDF reports. Numerical answers are calculated from your organization's data rather than guessed.",self._followups()
        if intent==Intent.WEBSITE:return "Sentinel AI is a tenant-isolated business intelligence platform. Use **Data Sources** to upload CSV or Excel data, the **Dashboard** to inspect KPIs, **Export PDF** to create reports, and this assistant to ask natural-language questions about your private organization data.",["How do I upload a dataset?","How do I export a PDF?"]
        if intent==Intent.REPORT:return "Sentinel reports are generated from your organization's current analytics and stored as protected PDFs. Use **Export PDF** to create one, **Share Report** to send it, or ask me about a specific metric shown in the report.",["Generate a report","Explain gross margin","Summarize my data"]
        return "I can help, but I need a little more context. Are you asking about using Sentinel, an uploaded dataset, a dashboard KPI, or a PDF report?",["What can you do?","Analyze my dataset","Help with a report"]

    def _dataset_answer(self,question:str,history:list[ChatMessage])->tuple[str,list[str]]:
        prior=[message.content for message in history if message.role=="user"]
        source,sources=self.datasets.select_source(question,prior)
        if not sources:
            overview=self.analytics.overview(None,None)
            if overview["order_count"]:
                products=self.analytics.products(None,None,10);regions=self.analytics.regions(None,None);q=question.lower()
                if "cancel" in q:return "I can't determine cancellations from the normalized records because that source column isn't available. Upload the original Sentinel CSV or Excel dataset to analyze cancellations.",[]
                if "product" in q and products:
                    top=products[0];return f"**{top['product']}** performed best by revenue at **{self._number(top['revenue'])}**, based on this organization's normalized sales records.",self._followups()
                if "region" in q and regions:
                    top=regions[0];return f"**{top['region']}** has the highest revenue at **{self._number(top['revenue'])}**, based on this organization's normalized sales records.",self._followups()
                return f"Your organization's total recognized revenue is **${self._number(overview['revenue'])}** across **{overview['order_count']:,} orders**. Average order value is **${self._number(overview['average_order_value'])}**.",self._followups()
            return "I can't analyze business numbers yet because this organization has no completed CSV or Excel import. Upload a dataset in **Data Sources**, then ask again.",["How do I upload a dataset?","What columns are required?"]
        if source is None:
            names=", ".join(f"**{item.name}**" for item in sources)
            return f"I found multiple active datasets: {names}. Which dataset would you like me to analyze? Please include its filename in your reply.",[item.name for item in sources[:3]]
        try:frame=self.datasets.load(source)
        except Exception:return f"I found **{source.name}**, but it could not be read safely. Re-upload a valid CSV or Excel file and try again.",[]
        q=question.lower();required={"Date","Revenue","Orders","Cancelled","Region","Product","Customer"}
        missing=required-set(frame.columns)
        if missing:return "I can't determine that from the uploaded data because the required information isn't available.",[]
        clean=frame.dropna(subset=["Revenue","Orders","Cancelled"]);name=f"**{source.name}**"
        if clean.empty:return f"{name} has no valid numeric business records to analyze.",[]
        total_revenue=float(clean["Revenue"].sum());orders=float(clean["Orders"].sum());cancelled=float(clean["Cancelled"].sum())
        intent=self.detector.detect(question)
        if intent==Intent.SENTIMENT:
            sentiment=analyze_sentiment(frame)
            if not sentiment["available"]:return sentiment["message"],[]
            distribution=", ".join(f"{item['label']}: {item['value']:,}" for item in sentiment["distribution"])
            return f"Customer sentiment in {name} is **{sentiment['score']:.1f}/100 — {sentiment['label']}**. It was calculated from **{sentiment['sample_count']:,}** values in `{sentiment['source_column']}` using {sentiment['method']}. Distribution: {distribution}.",["Why is sentiment negative?","What are the business risks?","Summarize my data"]
        if intent==Intent.RISK:
            risks=analyze_business_risks(frame)
            return risk_markdown(source.name,risks),["What data supports that conclusion?","Give me recommendations","Are there unusual patterns?"]
        if "cancel" in q:
            return f"{name} contains **{self._integer(cancelled)} cancelled orders** out of **{self._integer(orders)} total orders**.",self._followups()
        if ("average" in q or "avg" in q) and "order" in q:
            return f"The average order count per record in {name} is **{self._number(clean['Orders'].mean())}** across **{len(clean):,} records**.",self._followups()
        if "region" in q and any(term in q for term in ("highest","best","top","most","maximum","max","worst","lowest","weak")):
            ascending=any(term in q for term in ("worst","lowest","weak"));grouped=clean.groupby("Region",dropna=False)["Revenue"].sum().sort_values(ascending=ascending)
            if grouped.empty:return "I can't determine regional performance because usable Region values aren't available.",[]
            return f"**{grouped.index[0]}** has the {'lowest' if ascending else 'highest'} revenue in {name} at **{self._number(grouped.iloc[0])}**. This is calculated by grouping every record by Region and summing Revenue.",self._followups()
        if "product" in q and any(term in q for term in ("best","top","most","highest","performed","sold","worst","lowest","weak")):
            metric="Orders" if "sold" in q or "order" in q else "Revenue";ascending=any(term in q for term in ("worst","lowest","weak"));grouped=clean.groupby("Product",dropna=False)[metric].sum().sort_values(ascending=ascending)
            if grouped.empty:return "I can't determine product performance because usable Product values aren't available.",[]
            return f"**{grouped.index[0]}** is the {'worst' if ascending else 'leading'} product in {name} by {metric.lower()}, with **{self._number(grouped.iloc[0]) if metric=='Revenue' else self._integer(grouped.iloc[0])}**.",self._followups()
        if "customer" in q and any(term in q for term in ("top","most","highest","best")):
            match=re.search(r"top\s+(\d+)",q);limit=min(int(match.group(1)),20) if match else 1;grouped=clean.groupby("Customer",dropna=False)["Revenue"].sum().sort_values(ascending=False).head(limit)
            if grouped.empty:return "I can't determine customer performance because usable Customer values aren't available.",[]
            if limit==1:return f"**{grouped.index[0]}** generated the most revenue in {name}: **{self._number(grouped.iloc[0])}**.",self._followups()
            table="\n".join(f"| {index} | {customer} | {self._number(value)} |" for index,(customer,value) in enumerate(grouped.items(),1))
            return f"### Top {len(grouped)} customers in {name}\n\n| Rank | Customer | Revenue |\n|---:|---|---:|\n{table}",self._followups()
        if any(term in q for term in ("decrease","decline","down","increase","growth","change","trend")):
            dated=clean.dropna(subset=["Date"]).groupby("Date")["Revenue"].sum().sort_index()
            if len(dated)<2:return "I can't determine a revenue trend from this dataset because at least two valid dates are required.",[]
            first,last=float(dated.iloc[0]),float(dated.iloc[-1]);difference=last-first;percent=(difference/first*100) if first else None;direction="increased" if difference>=0 else "decreased"
            suffix=f" (**{abs(percent):.2f}%**)" if percent is not None else ""
            return f"Revenue {direction} by **{self._number(abs(difference))}**{suffix}, from **{self._number(first)}** on {dated.index[0].date()} to **{self._number(last)}** on {dated.index[-1].date()}. This describes the measured change; the available columns do not prove a business cause.",self._followups()
        if "summar" in q or "analy" in q or "kpi" in q or "file" in q or "data" in q:
            regions=clean.groupby("Region")["Revenue"].sum().sort_values(ascending=False);products=clean.groupby("Product")["Revenue"].sum().sort_values(ascending=False)
            profile=profile_dataset(frame)
            return f"### Summary of {name}\n\n- **Records:** {len(clean):,}\n- **Columns:** {profile['column_count']} ({', '.join(profile['columns'])})\n- **Total revenue:** {self._number(total_revenue)}\n- **Total orders:** {self._integer(orders)}\n- **Cancelled orders:** {self._integer(cancelled)}\n- **Average revenue per record:** {self._number(clean['Revenue'].mean())}\n- **Highest-revenue region:** {regions.index[0] if not regions.empty else 'Unavailable'}\n- **Highest-revenue product:** {products.index[0] if not products.empty else 'Unavailable'}\n- **Missing values:** {sum(profile['missing_values'].values()):,}\n- **Duplicate rows:** {profile['duplicate_rows']:,}",self._followups()
        if "revenue" in q or "sales" in q or "total" in q or "sum" in q:
            return f"The total revenue in {name} is **{self._number(total_revenue)}**. The file contains **{self._integer(orders)} orders**, including **{self._integer(cancelled)} cancellations**.",self._followups()
        if "count" in q and "record" in q:return f"{name} contains **{len(clean):,} valid records**.",self._followups()
        return "I can't determine the requested result from the available columns. Try naming the metric and operation—for example, total revenue, average orders, top region, top product, cancellations, or top customers.",self._followups()

    def _optional_local_model(self,question:str,answer:str,history:list[ChatMessage])->str:
        return self.model.complete(question,answer,[{"role":message.role,"content":message.content} for message in history])

    def chat(self,question:str,conversation_id:UUID|None)->tuple[ChatConversation,ChatMessage,list[str]]:
        conversation=self._conversation(conversation_id,question);history=list(self.db.scalars(select(ChatMessage).where(ChatMessage.conversation_id==conversation.id,ChatMessage.organization_id==self.organization_id).order_by(ChatMessage.created_at)))
        self.db.add(ChatMessage(organization_id=self.organization_id,conversation_id=conversation.id,role="user",content=question.strip()))
        intent=self.detector.detect(question)
        if intent in {Intent.DATA,Intent.RISK,Intent.SENTIMENT}:answer,followups=self._dataset_answer(question,history)
        else:
            answer,followups=self._normal_answer(intent)
            if intent==Intent.UNKNOWN:answer=self._optional_local_model(question,answer,history)
        assistant=ChatMessage(organization_id=self.organization_id,conversation_id=conversation.id,role="assistant",content=answer);self.db.add(assistant);self.db.commit();self.db.refresh(assistant);self.db.refresh(conversation);return conversation,assistant,followups

    def forecast(self,horizon:int)->dict:
        rows=self.repository.daily_revenue(None,None)
        if len(rows)<2:return {"method":"linear-trend-v1","horizon_days":horizon,"points":[],"warning":"At least two days of sales history are required."}
        values=[float(row["revenue"] or 0) for row in rows];n=len(values);x_mean=(n-1)/2;y_mean=mean(values);denominator=sum((i-x_mean)**2 for i in range(n));slope=sum((i-x_mean)*(value-y_mean) for i,value in enumerate(values))/denominator if denominator else 0;intercept=y_mean-slope*x_mean;last_date=rows[-1]["date"]
        return {"method":"linear-trend-v1","horizon_days":horizon,"points":[{"date":str(last_date+timedelta(days=day)),"value":round(max(0,intercept+slope*(n-1+day)),2)} for day in range(1,horizon+1)],"warning":"Statistical trend projection; not a financial guarantee."}

    def anomalies(self,threshold:float=2.5)->dict:
        rows=self.repository.daily_revenue(None,None);values=[float(row["revenue"] or 0) for row in rows];deviation=pstdev(values) if len(values)>1 else 0;average=mean(values) if values else 0;items=[] if not deviation else [{"date":str(row["date"]),"revenue":round(value,2),"z_score":round((value-average)/deviation,3),"direction":"high" if value>average else "low"} for row,value in zip(rows,values) if abs((value-average)/deviation)>=threshold];return {"method":f"z-score-{threshold}","items":items,"count":len(items)}

    def dataset_intelligence(self)->dict:
        sources=self.datasets.active_sources();frame=self.datasets.load_active()
        return {"datasets":[source.name for source in sources],"profile":profile_dataset(frame),"sentiment":analyze_sentiment(frame),"risks":analyze_business_risks(frame)}
