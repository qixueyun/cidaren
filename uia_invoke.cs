using System;
using System.Runtime.InteropServices;
using System.Windows.Automation;
class UIAInvoke {
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [StructLayout(LayoutKind.Sequential)] struct Point { public int x,y; }
 [DllImport("user32.dll")] static extern bool GetCursorPos(out Point p);
 [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
 [StructLayout(LayoutKind.Sequential)] struct Rect {public int left,top,right,bottom;}
 [DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr h,out Rect r);
 [STAThread] static int Main(string[] args) {
  try {
   SetProcessDPIAware();
   if(args[1]=="points") {
    for(int i=2;i<args.Length;i+=2) {
     if(i+1>=args.Length||Main(new string[]{args[0],"point",args[i],args[i+1]})!=0)
      throw new Exception("Batch partially applied; reobserve selection page");
     System.Threading.Thread.Sleep(40);
    }
    return 0;
   }
   var root=AutomationElement.FromHandle(new IntPtr(long.Parse(args[0])));
   if(args[1]=="scroll-down") {
    var scrolls=root.FindAll(TreeScope.Subtree,new PropertyCondition(AutomationElement.IsScrollPatternAvailableProperty,true));
    AutomationElement chosen=null;double area=0;
    for(int i=0;i<scrolls.Count;i++) {
     object value;if(!scrolls[i].TryGetCurrentPattern(ScrollPattern.Pattern,out value))continue;
     var s=(ScrollPattern)value;var b=scrolls[i].Current.BoundingRectangle;
     if(s.Current.VerticallyScrollable&&!scrolls[i].Current.IsOffscreen&&b.Width*b.Height>area) {
      chosen=scrolls[i];area=b.Width*b.Height;
     }
    }
    if(chosen==null)throw new Exception("Task list has no accessible vertical scroll control");
    var scroll=(ScrollPattern)chosen.GetCurrentPattern(ScrollPattern.Pattern);
    if(scroll.Current.VerticalScrollPercent>=99.9){Console.WriteLine("SCROLL_END");return 0;}
    scroll.Scroll(ScrollAmount.NoAmount,ScrollAmount.LargeIncrement);
    Console.WriteLine("SCROLLED");return 0;
   }
   string name=args[1]=="menu"?"\ue628":args[1];
   AutomationElement target=null;object pattern;
   if(name=="point") {
    Rect frame;GetWindowRect(new IntPtr(long.Parse(args[0])),out frame);
    double x=frame.left+double.Parse(args[2],System.Globalization.CultureInfo.InvariantCulture);
    double y=frame.top+double.Parse(args[3],System.Globalization.CultureInfo.InvariantCulture);
    if(x<frame.left||x>=frame.right||y<frame.top||y>=frame.bottom)throw new Exception("Point outside selected window");
    var all=root.FindAll(TreeScope.Descendants,new AndCondition(
     new PropertyCondition(AutomationElement.IsInvokePatternAvailableProperty,true),
     new PropertyCondition(AutomationElement.IsOffscreenProperty,false)));double best=Double.MaxValue;
    for(int i=0;i<all.Count;i++) {
     var b=all[i].Current.BoundingRectangle;object candidate;
     if(!all[i].Current.IsOffscreen&&b.Width>0&&b.Height>0&&x>=b.Left&&x<=b.Right&&y>=b.Top&&y<=b.Bottom&&
        b.Width*b.Height<=best&&all[i].TryGetCurrentPattern(InvokePattern.Pattern,out candidate)) {
      target=all[i];best=b.Width*b.Height;
     }
    }
    if(target==null)throw new Exception("No invokable element at observed point");
   }else if(name=="dismiss-overlay") {
    var groups=root.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Group));
    var bounds=root.Current.BoundingRectangle;int found=0;
    for(int i=0;i<groups.Count;i++) {
     var box=groups[i].Current.BoundingRectangle;object candidate;
     if(String.IsNullOrEmpty(groups[i].Current.Name)&&box.Width>bounds.Width*.8&&box.Height>bounds.Height*.8&&
        groups[i].TryGetCurrentPattern(InvokePattern.Pattern,out candidate)){target=groups[i];found++;}
    }
    if(found!=1)throw new Exception("Expected one menu overlay; got "+found);
   }else {
    var matches=root.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.NameProperty,name));
    if(matches.Count!=1)throw new Exception("Expected one matching text element; got "+matches.Count);
    target=matches[0];
   }
   for(int depth=0;depth<5;depth++) {
    if(target.TryGetCurrentPattern(InvokePattern.Pattern,out pattern)) {
     IntPtr foreground=GetForegroundWindow();Point before,after;GetCursorPos(out before);
     ((InvokePattern)pattern).Invoke();
     GetCursorPos(out after);
     Console.WriteLine("INVOKED foreground_unchanged="+(foreground==GetForegroundWindow())+
                       " cursor_unchanged="+(before.x==after.x&&before.y==after.y));
     return 0;
    }
    target=TreeWalker.ControlViewWalker.GetParent(target);
    if(target==null||target.Current.ControlType==ControlType.Document)break;
   }
   throw new Exception("No invokable control found for observed text");
  }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}
 }
}
