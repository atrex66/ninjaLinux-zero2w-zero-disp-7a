#include <QGuiApplication>
#include <QOpenGLWindow>
#include <QSurfaceFormat>
#include <QOpenGLFunctions>
#include <QPainter>
#include <QTimer>
#include <QElapsedTimer>
#include <QTouchEvent>
#include <QMouseEvent>
#include <QDebug>
#include <QFile>
#include <cmath>
#include <sys/utsname.h>
class Demo final : public QOpenGLWindow, protected QOpenGLFunctions {
 QElapsedTimer elapsed;
 QPointF point{512,300};
 QString renderer;
 int touches=0;
 bool firstFrame=true;
public:
 Demo() { elapsed.start(); auto *t=new QTimer(this); connect(t,&QTimer::timeout,this,[this]{update();}); t->start(16); }
 void initializeGL() override {
  initializeOpenGLFunctions();
  renderer=QString::fromLatin1(reinterpret_cast<const char*>(glGetString(GL_RENDERER)));
  qInfo()<<"GL_RENDERER:"<<renderer;
  if(renderer.contains("llvmpipe",Qt::CaseInsensitive)||renderer.contains("softpipe",Qt::CaseInsensitive)) qCritical()<<"SOFTWARE RENDERER: hardware graphics test FAILED";
 }
 void paintGL() override {
  if(firstFrame) { QFile uptime("/proc/uptime"); if(uptime.open(QIODevice::ReadOnly)) qInfo()<<"FIRST_FRAME_KERNEL_UPTIME:"<<uptime.readAll().trimmed(); firstFrame=false; }
  glClearColor(0.025f,0.045f,0.075f,1.f); glClear(GL_COLOR_BUFFER_BIT);
  QPainter p(this); p.setRenderHint(QPainter::Antialiasing);
  p.setPen(Qt::white); p.setFont(QFont("DejaVu Sans",28));
  p.drawText(QRect(40,30,width()-80,65),Qt::AlignLeft,"FastLinux / Zero 2 W");
  p.setFont(QFont("DejaVu Sans",16));
  p.drawText(QRect(40,110,width()-80,85),Qt::TextWordWrap,"GPU: "+renderer);
  struct utsname kernel; bool realtime=uname(&kernel)==0 && QByteArray(kernel.version).contains("PREEMPT_RT");
  p.drawText(40,225,realtime ? "Kernel: PREEMPT_RT" : "Kernel: normal");
  p.drawText(40,265,QString("Touch / mouse events: %1").arg(touches));
  p.drawText(40,height()-35,QString("UI elapsed: %1 s | 1024 x 600 target").arg(elapsed.elapsed()/1000.0,0,'f',1));
  double a=elapsed.elapsed()/600.0;
  p.setPen(Qt::NoPen); p.setBrush(QColor("#29c7bd"));
  p.drawEllipse(QPointF(width()/2.0+140*std::cos(a),height()/2.0+85*std::sin(a)),28,28);
  p.setBrush(QColor("#ffb454")); p.drawEllipse(point,18,18);
 }
 bool event(QEvent *e) override {
  if(e->type()==QEvent::TouchBegin || e->type()==QEvent::TouchUpdate || e->type()==QEvent::TouchEnd) {
   auto *t=static_cast<QTouchEvent*>(e); if(!t->points().isEmpty()) point=t->points().first().position(); ++touches; e->accept(); update(); return true;
  }
  return QOpenGLWindow::event(e);
 }
 void mousePressEvent(QMouseEvent *e) override {point=e->position(); ++touches; update();}
};
int main(int argc,char **argv) {
 QSurfaceFormat fmt; fmt.setRenderableType(QSurfaceFormat::OpenGLES); fmt.setVersion(2,0); fmt.setSwapInterval(1); QSurfaceFormat::setDefaultFormat(fmt);
 QGuiApplication app(argc,argv); Demo w; w.showFullScreen(); return app.exec();
}
