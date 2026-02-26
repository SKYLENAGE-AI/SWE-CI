if __name__ == "__main__":

    from swe_ci.benchmark import init_tasks, run_tasks, summarize

    if not init_tasks():
        print("Failed to initialize completely, please try again.", flush=True)
        exit(0)
    while not run_tasks():
        pass
    summarize()
