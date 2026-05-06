"""SEC EDGAR data provider — Form 4 insider transactions and 13F guru holdings."""
import re
import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

_log = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "ValueScreen info@valuescreen.com", "Accept-Encoding": "gzip"}

TRANSACTION_CODES = {
    "P": "Purchase", "S": "Sale", "A": "Award/Grant",
    "M": "Option Exercise", "F": "Tax Sale (Withholding)",
    "G": "Gift", "C": "Conversion", "D": "Disposition",
    "X": "Option Exercise", "W": "Warrant Exercise",
}

# Known value investor funds: CIK → (guru name, fund name)
GURU_CIKS = {
    "1067983": ("Warren Buffett",    "Berkshire Hathaway"),
    "1336528": ("Bill Ackman",       "Pershing Square"),
    "1101955": ("Seth Klarman",      "Baupost Group"),
    "1418814": ("David Tepper",      "Appaloosa Management"),
    "1603466": ("Dan Loeb",          "Third Point"),
    "1079114": ("David Einhorn",     "Greenlight Capital"),
    "913760":  ("Joel Greenblatt",   "Gotham Asset Management"),
    "1061219": ("Dodge & Cox",       "Dodge & Cox"),
    "814156":  ("Mario Gabelli",     "Gabelli Funds"),
    "886744":  ("Chuck Royce",       "Royce & Associates"),
    "1397187": ("Bill Nygren",       "Oakmark Funds"),
    "885521":  ("Donald Yacktman",   "Yacktman Asset Management"),
    "1048268": ("John Rogers",       "Ariel Investments"),
    "1159159": ("Wally Weitz",       "Weitz Investment Management"),
    "921669":  ("First Eagle",       "First Eagle Investment"),
    "0000883237": ("Tom Gayner",     "Markel Corporation"),
}


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    r = await client.get(url)
    r.raise_for_status()
    return r


async def _parse_form4(client: httpx.AsyncClient, filing_url: str) -> list[dict]:
    """Parse a Form 4 index page and return its transactions."""
    try:
        r = await _get(client, filing_url)
        # Find raw XML (not the XSLT-rendered version)
        xml_hrefs = [h for h in re.findall(r'href="(/Archives/[^"]+\.xml)"', r.text)
                     if "xslF345X06" not in h]
        if not xml_hrefs:
            return []
        xml_url = "https://www.sec.gov" + xml_hrefs[0]
        rx = await _get(client, xml_url)
        root = ET.fromstring(rx.content)

        name = (root.findtext(".//rptOwnerName") or "").strip()
        if root.findtext(".//isOfficer") == "true":
            position = root.findtext(".//officerTitle") or "Officer"
        elif root.findtext(".//isDirector") == "true":
            position = "Director"
        elif root.findtext(".//isTenPercentOwner") == "true":
            position = "10% Owner"
        else:
            position = None

        transactions = []
        for tx in root.findall(".//nonDerivativeTransaction"):
            date  = tx.findtext(".//transactionDate/value") or ""
            code  = tx.findtext(".//transactionCode") or ""
            raw_shares = tx.findtext(".//transactionShares/value") or ""
            raw_price  = tx.findtext(".//transactionPricePerShare/value") or ""
            try:
                shares = float(raw_shares) if raw_shares else None
                price  = float(raw_price)  if raw_price  else None
                value  = shares * price if shares and price else None
            except ValueError:
                shares = price = value = None

            transactions.append({
                "name": name,
                "position": position,
                "transaction_type": TRANSACTION_CODES.get(code, code or None),
                "shares": shares,
                "value": value,
                "date": date[:10] if date else None,
            })
        return transactions
    except Exception as exc:
        _log.debug("Form 4 parse error for %s: %s", filing_url, exc)
        return []


async def get_insider_transactions(ticker: str) -> list[dict]:
    """Return past-12-month insider transactions from SEC EDGAR Form 4 filings."""
    cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    atom_url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?company=&CIK={ticker}&type=4&dateb=&owner=include"
        f"&count=20&search_text=&action=getcompany&output=atom"
    )
    async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
        try:
            r = await _get(client, atom_url)
            # Pull filing index URLs and their dates from the Atom feed
            dates = re.findall(r"<updated>(\d{4}-\d{2}-\d{2})", r.text)
            hrefs = re.findall(
                r'href="(https://www\.sec\.gov/Archives/edgar/data/[^"]+index\.htm)"',
                r.text
            )
            valid_hrefs = [h for i, h in enumerate(hrefs) if i < len(dates) and dates[i] >= cutoff]

            if not valid_hrefs:
                return []

            results = await asyncio.gather(
                *[_parse_form4(client, h) for h in valid_hrefs[:15]],
                return_exceptions=True
            )
            txns = [t for res in results if isinstance(res, list) for t in res]
            txns.sort(key=lambda x: x.get("date") or "", reverse=True)
            return txns[:30]
        except Exception as exc:
            _log.warning("SEC EDGAR insider fetch failed for %s: %s", ticker, exc)
            return []


async def _check_guru_holding(client: httpx.AsyncClient, guru_cik: str, ticker: str) -> dict | None:
    """Check the latest 13F filing of a guru fund for a given ticker."""
    try:
        r = await _get(client, f"https://data.sec.gov/submissions/CIK{guru_cik.zfill(10)}.json")
        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        acc_nos = filings.get("accessionNumber", [])

        # Get the most recent 13F-HR
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                acc = acc_nos[i].replace("-", "")
                cik_int = str(int(guru_cik))
                index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{acc_nos[i]}-index.htm"
                ri = await _get(client, index_url)
                # Find the primary XML (infotable)
                xml_hrefs = [h for h in re.findall(r'href="(/Archives/[^"]+\.xml)"', ri.text)
                             if "primary_doc" not in h.lower()]
                for xhref in xml_hrefs:
                    try:
                        rx = await _get(client, "https://www.sec.gov" + xhref)
                        content = rx.text
                        # Simple regex search — parsing full 13F XML is slow
                        ticker_upper = ticker.upper()
                        # Look for the ticker in the infotable XML
                        if ticker_upper not in content.upper():
                            continue
                        # Find shares and value for this ticker
                        pattern = (
                            rf"<nameOfIssuer>[^<]*{re.escape(ticker_upper)}[^<]*</nameOfIssuer>"
                            r".*?<value>(\d+)</value>.*?<sshPrnamt>(\d+)</sshPrnamt>"
                        )
                        m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                        if m:
                            value_thou = int(m.group(1))  # in thousands
                            shares = int(m.group(2))
                            return {
                                "value": value_thou * 1000,
                                "shares": shares,
                                "date_reported": dates[i],
                            }
                    except Exception:
                        continue
                break
    except Exception as exc:
        _log.debug("13F check failed for guru CIK %s: %s", guru_cik, exc)
    return None


async def get_guru_holdings(ticker: str) -> list[dict]:
    """Return known guru funds that hold the given ticker (from latest 13F filings)."""
    async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
        tasks = {
            cik: _check_guru_holding(client, cik, ticker)
            for cik in GURU_CIKS
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        gurus = []
        for cik, result in zip(tasks.keys(), results):
            if isinstance(result, dict) and result:
                guru_name, fund_name = GURU_CIKS[cik]
                gurus.append({
                    "holder": fund_name,
                    "guru": guru_name,
                    "shares": result["shares"],
                    "value": result["value"],
                    "pct_out": None,
                    "date_reported": result["date_reported"],
                })
        gurus.sort(key=lambda x: x.get("value") or 0, reverse=True)
        return gurus
