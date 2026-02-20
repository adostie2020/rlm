import queue
import threading
import time
from typing import Any, Callable, Generator

class StreamCapturer:
    """
    A file-like object that writes to a queue.
    Used to capture stdout/stderr or rich Console output for streaming.
    """
    def __init__(self, queue_instance: queue.Queue):
        self.queue = queue_instance

    def write(self, text: str):
        if text:
            self.queue.put(text)

    def flush(self):
        pass

    def isatty(self):
        return False

class ThreadedStreamer:
    """
    Runs a target function in a background thread and yields captured output
    from a queue as a generator.
    """
    def __init__(self, target: Callable, *args, protocol: str = "text", **kwargs):
        self.queue = queue.Queue()
        self.target = target
        self.protocol = protocol
        self.args = args
        self.kwargs = kwargs
        self.capturer = StreamCapturer(self.queue)
        self.thread = threading.Thread(target=self._run_target)
        self.finished = False
        self.error = None

    def _run_target(self):
        try:
            # Execute the target function
            # The target function is expected to use self.capturer (passed via args/kwargs or context)
            # to write its output.
            self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.error = e
            import traceback
            traceback.print_exc()
            self.queue.put(f"\nError in execution: {e}\n")
        finally:
            self.finished = True
            # Put a sentinel or just rely on finished flag
            # We add a small delay to ensure queue is drained properly in the loop

    def stream_generator(self) -> Generator[str, None, None]:
        """
        Yields chunks of text from the queue until the thread finishes and queue is empty.
        Adheres to Vercel AI SDK Data Stream Protocol.
        """
        self.thread.start()
        
        while not self.finished or not self.queue.empty():
            try:
                # Wait for data with a timeout to check finished status
                chunk = self.queue.get(timeout=0.1)
                if chunk:
                    import json
                    if self.protocol == "vercel_data_stream":
                        # Vercel Data Stream Protocol
                        yield f'data: {json.dumps({"type": "text", "text": chunk})}\n\n'
                    else:
                        # Default / Legacy "text" behavior (Vercel Stream Data - v1)
                        # 0:"encoded_text"\n
                        encoded_chunk = json.dumps(chunk)
                        yield f'0:{encoded_chunk}\n'
            except queue.Empty:
                continue
        
        if self.error:
            # Optionally yield error part? 
            # For now we just logged it to stream.
            pass
            
        if self.protocol == "vercel_data_stream":
            yield 'data: [DONE]\n\n'
