const $ = id => document.getElementById(id);
const source = $('sourceCode'), output = $('outputCode');
const sample = `#include <iostream>
using namespace std;

int main() {
    int x = 10;
    int y = 20;
    int total = 10 + 20;
    int copy = total;
    int result = copy * 1;
    int unused = 99;
    int answer = result + 0;
    cout << answer << endl;
    return 0;
}`;
function updateCounts(){ $('inputCount').textContent = `${source.value.split('\\n').length} lines`; }
source.addEventListener('input', updateCounts);
$('sampleBtn').onclick = () => { source.value = sample; updateCounts(); $('message').textContent = 'Sample C++ program loaded.'; };
$('clearBtn').onclick = () => { source.value=''; output.value=''; updateCounts(); $('message').textContent='Editor cleared.'; };
$('optimizeBtn').onclick = async () => {
  $('message').textContent='Optimizing…';
  try {
    const res = await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:source.value})});
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || 'Unable to optimize code.');
    output.value=data.optimized_code;
    $('statOpt').textContent=data.summary.optimizations;
    $('statRemoved').textContent=data.summary.lines_removed;
    $('statLines').textContent=data.summary.optimized_lines;
    $('outputCount').textContent=`${data.summary.optimized_lines} non-empty lines`;
    $('reportCount').textContent=`${data.report.length} changes`;
    const list=$('reportList'); list.innerHTML='';
    if(!data.report.length) list.innerHTML='<div class="empty">No supported optimization was found. Try the sample program or simpler arithmetic statements.</div>';
    data.report.forEach(item=>{
      const el=document.createElement('div'); el.className='report-item';
      const title=document.createElement('strong'); title.textContent=item.technique;
      const detail=document.createElement('p'); detail.textContent=item.detail;
      const line=document.createElement('small'); line.textContent=`Original line ${item.line}`;
      el.append(title,detail,line); list.append(el);
    });
    $('message').textContent=`Done — ${data.summary.optimizations} optimization(s) applied.`;
  } catch(e){ $('message').textContent=e.message; }
};
$('copyBtn').onclick=async()=>{if(!output.value)return;await navigator.clipboard.writeText(output.value);$('message').textContent='Optimized code copied.';};
$('downloadBtn').onclick=async()=>{
  if(!output.value){$('message').textContent='Optimize code first.';return;}
  const blob=new Blob([output.value],{type:'text/plain'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='optimized.cpp';a.click();URL.revokeObjectURL(url);
};
$('validateBtn').onclick=async()=>{
  if(!source.value.trim()){$('message').textContent='Enter C++ code first.';return;}
  $('message').textContent='Checking C++ syntax…';
  try{
    const res=await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:output.value||source.value})});
    const data=await res.json(); $('message').textContent=data.message;
  }catch(e){$('message').textContent='Validation request failed.';}
};
updateCounts();
