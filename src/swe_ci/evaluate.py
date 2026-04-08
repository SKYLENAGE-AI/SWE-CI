if __name__ == "__main__":

    import json
    from swe_ci.benchmark import init_tasks, run_tasks, summarize

    if not init_tasks():
        print("Failed to initialize completely, please try again.", flush=True)
        exit(0)
    while not run_tasks():
        pass
        
    summary = summarize()

    res = {
        "score": summary[0]["metrics"]["EvoScore(gamma=1)"],
        "reason": summary[0]["iterations"]
    }
    
    with open("./summary.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
