using System;
using System.Windows.Automation;
class InspectUIA {
 [STAThread] static void Main(string[] args) {
  var root=AutomationElement.FromHandle(new IntPtr(long.Parse(args[0])));
  var all=root.FindAll(TreeScope.Descendants,Condition.TrueCondition);
  for(int i=0;i<all.Count;i++) {
   var e=all[i];
   string actions="";
   foreach(var p in e.GetSupportedPatterns()) actions+=p.ProgrammaticName+",";
   string def="";
   Console.WriteLine(i+"|"+e.Current.ControlType.ProgrammaticName+"|"+e.Current.Name.Replace("\n"," ")+"|"+e.Current.AutomationId+"|"+actions+"|"+def+"|"+e.Current.BoundingRectangle);
  }
 }
}
